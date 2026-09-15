# ============================================================
# RENDERERS
# ============================================================

def render_value(field, value):

    descriptor = field["descriptor"]

    return [
        f"{descriptor} {value}"
    ]


def render_boolean_enable_disable(field, value):
    if value is None:
        return []

    if value is True:
        return [
            field["descriptor"]
        ]

    return [
        f"no {field['descriptor']}"
    ]

def render_boolean_enable(field, value):
    if value is None or value is False:
        return []
    else:
        return [
            field["descriptor"]
        ]

def render_delimited(field, value):

    if value is None:
        return []

    descriptor = field["descriptor"]

    return [
        f"{descriptor} #{value}#"
    ]

def render_multiple(field, value):

    if value is None:
        return []

    commands = []

    for command in field["commands"]:
        commands.append(
            command.format(value=value)
        )

    return commands

def render_structured_multiple(field, value):
    if value is None:
        return []

    commands = []

    for command in field["commands"]:
        commands.append(command.format(**value))

    return commands


# ============================================================
# RENDER TEMPLATE
# ============================================================
#
# Para campos virtuales (los que tienen "requires"): recibe un
# dict con todos los valores que el comando necesita, no un
# valor suelto.
#
#     {"ipv4": "172.17.10.1", "mask_ipv4": "255.255.255.0"}
#     -> "ip address 172.17.10.1 255.255.255.0"
#
# ============================================================

def render_template(field, values):

    if values is None:
        return []

    commands = []

    for command in field["commands"]:
        commands.append(command.format(**values))

    return commands

# ============================================================
# RENDER DISPATCH
# ============================================================

RENDER_FUNCTIONS = {

    "value": render_value,

    "boolean_enable_disable":
        render_boolean_enable_disable,

    "delimited":
        render_delimited,

    "multiple":
        render_multiple,

    "boolean_enable":
        render_boolean_enable,

    "structured_multiple":
        render_structured_multiple,

    "template":
        render_template
}

# ============================================================
# RENDER FIELD
# ============================================================

def render_field(field, value):

    if value is None:
        return []

    render_type = field.get("render")

    if render_type is None:
        return []

    render_function = RENDER_FUNCTIONS[
        render_type
    ]

    return render_function(
        field,
        value
    )
