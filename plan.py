import render
import catalog


# ============================================================
# BUILD PLAN
# ============================================================
#
# Devuelve una lista de bloques:
#
# [
#     {"mode": "global_config", "commands": [...]},
#     {"mode": "vlan",      "arg": "10",     "commands": [...]},
#     {"mode": "interface", "arg": "g0/1",   "commands": [...]}
# ]
#
# ============================================================

def build_plan(device):

    blocks = {}
    ordered_modes = []

    # --------------------------------------------------------
    # CAMPOS PLANOS DEL DEVICE
    # --------------------------------------------------------

    for field_name, value in device.items():

        if field_name in ("type", "interfaces", "vlans"):
            continue

        if value is None:
            continue

        field = catalog.resolve_field(field_name, device["type"])

        mode = field.get("mode")

        if mode is None:
            continue

        commands = render.render_field(field, value)

        if not commands:
            continue

        if mode not in blocks:
            blocks[mode] = []
            ordered_modes.append(mode)

        blocks[mode].extend(commands)

    plan = [
        {"mode": mode, "commands": blocks[mode]}
        for mode in ordered_modes
    ]

    # --------------------------------------------------------
    # VLANS
    # --------------------------------------------------------
    #
    # Van antes que las interfaces: si un puerto referencia una
    # VLAN inexistente el IOS la crea igual, pero sin nombre.
    #
    # Un bloque de VLAN puede quedar sin comandos (VLAN sin
    # nombre) y aun asi hay que emitirlo, porque el "vlan N"
    # es la creacion en si.
    # --------------------------------------------------------

    for vlan in device.get("vlans") or []:

        commands = []

        if vlan.get("name"):
            field = catalog.resolve_field("vlan_name", device["type"])
            commands.extend(render.render_field(field, vlan["name"]))

        plan.append({
            "mode": "vlan",
            "arg": str(vlan["id"]),
            "commands": commands
        })

    # --------------------------------------------------------
    # INTERFACES
    # --------------------------------------------------------

    for interface in device.get("interfaces") or []:

        commands = build_interface_commands(interface, device["type"])

        if not commands:
            continue

        mode = "interface_range" if "-" in interface["name"] else "interface"

        plan.append({
            "mode": mode,
            "arg": interface["name"],
            "commands": commands
        })

    return plan


# ============================================================
# BUILD INTERFACE COMMANDS
# ============================================================
#
# El orden de los comandos lo define role["fields"], no el
# orden en que el usuario cargo los datos. Importa: por ej.
# "switchport mode access" tiene que salir antes que
# "switchport access vlan", y shutdown va ultimo.
#
# ============================================================

def build_interface_commands(interface, device_type):

    role = catalog.INTERFACE_ROLES[interface["role"]]

    commands = []

    for field_name in role["render_fields"]:

        field = catalog.resolve_field(field_name, device_type)

        requires = field.get("requires")

        if requires:

            # campo virtual: necesita todos sus valores; si
            # falta alguno el comando no se puede armar

            if any(interface.get(name) is None for name in requires):
                continue

            value = {name: interface[name] for name in requires}

        else:

            value = interface.get(field_name)

            if value is None:
                continue

        commands.extend(render.render_field(field, value))

    return commands
