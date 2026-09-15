import catalog
from plan import build_plan

# ============================================================
# PLAN TO TEXT
# ============================================================

def get_path(mode):

    path = []
    current = mode

    while current is not None:
        path.append(current)
        current = catalog.MODE_COMMANDS[current]["parent"]

    return list(reversed(path))

def plan_to_text(plan):

    lines = []
    current_path = []

    for block in plan:

        target_path = get_path(block["mode"])

        # el ultimo nodo lleva el arg; los padres no
        target_keys = [(mode, None) for mode in target_path[:-1]]
        target_keys.append((target_path[-1], block.get("arg")))

        # prefijo comun entre donde estoy y donde quiero ir
        common = 0
        while (common < len(current_path)
               and common < len(target_keys)
               and current_path[common] == target_keys[common]):
            common += 1

        # salir de los modos que sobran
        for i in range(len(current_path) - 1, common - 1, -1):
            lines.append(f'{" " * ((i + 1) * catalog.INDENT)}exit')

        # entrar a los modos que faltan
        for i in range(common, len(target_keys)):
            mode, arg = target_keys[i]
            enter = catalog.MODE_COMMANDS[mode]["enter"]

            if arg:
                enter = f"{enter}{arg}"

            lines.append(f'{" " * (i * catalog.INDENT)}{enter}')

        indent = " " * (len(target_keys) * catalog. INDENT)

        for command in block["commands"]:
            lines.append(f"{indent}{command}")

        current_path = target_keys

    lines.append(f'{" " * (2 * catalog.INDENT)}end')
    lines.append(f'{" " * catalog.INDENT}write memory')

    return "\n".join(lines)



# ============================================================
# BUILD CONFIG FILE
# ============================================================

def build_config_file(device):

    filtered = {
        k: v for k, v in device.items()
        if k not in catalog.NOT_IN_CONFIG_FILE
    }

    plan = build_plan(filtered)
    lines = ["!"]

    for block in plan:

        if block["mode"] == catalog.CONFIG_FILE_ROOT:
            for command in block["commands"]:
                lines.append(command)
        else:
            enter = catalog.MODE_COMMANDS[block["mode"]]["enter"]

            if block.get("arg"):
                enter = f"{enter}{block['arg']}"

            lines.append(enter)

            for command in block["commands"]:
                lines.append(f" {command}")

        lines.append("!")

    lines.append("end")

    return "\n".join(lines)
