import copy
import auxiliar


# ============================================================
# FIELD DEFINITIONS
# ============================================================

FIELD_DEFINITIONS = {

    # --------------------------------------------------------
    # HOSTNAME
    # --------------------------------------------------------

    "hostname": {
        "question": "Write the hostname",
        "validator": auxiliar.validate_hostname,

        "mode": "global_config",

        "render": "value",
        "descriptor": "hostname"
    },


    # --------------------------------------------------------
    # PASSWORD ENCRYPTION
    # --------------------------------------------------------

    "password_encryption": {
        "question": "Enable service password-encryption?",
        "validator": auxiliar.validate_yes_no,

        "mode": "global_config",

        "render": "boolean_enable_disable",
        "descriptor": "service password-encryption"
    },


    # --------------------------------------------------------
    # BANNER
    # --------------------------------------------------------

    "banner": {
        "question": "Write the banner",
        "validator": auxiliar.validate_optional_string,

        "mode": "global_config",

        "render": "delimited",
        "descriptor": "banner motd"
    },


    # --------------------------------------------------------
    # DNS LOOKUP
    # --------------------------------------------------------

    "dns_lookup": {
        "question": (
            "Enable DNS lookup? "
            "(yes = the device performs DNS lookups)"
        ),
        "validator": auxiliar.validate_yes_no,

        "mode": "global_config",

        "render": "boolean_enable_disable",
        "descriptor": "ip domain-lookup"
    },


    # --------------------------------------------------------
    # CONSOLE PASSWORD
    # --------------------------------------------------------

    "console_password": {
        "question": "Write the console password",
        "validator": auxiliar.validate_optional_string,

        "mode": "line_console",

        "render": "multiple",

        "commands": [
            "password {value}",
            "login"
        ]
    },


    # --------------------------------------------------------
    # VTY PASSWORD
    # --------------------------------------------------------

    "vty_password": {
        "question": "Write the VTY password",
        "validator": auxiliar.validate_optional_string,

        "mode": "line_vty",

        "render": "multiple",

        "commands": [
            "password {value}",
            "login"
        ]
    },


    # --------------------------------------------------------
    # PRIVILEGE PASSWORD
    # --------------------------------------------------------

    "privilege_password": {
        "question": "Write the privilege password",
        "validator": auxiliar.validate_optional_string,

        "mode": "global_config",

        "render": "value",
        "descriptor": "enable secret"
    },


    # --------------------------------------------------------
    # GATEWAY
    # --------------------------------------------------------

    "gateway": {
        "question": "Write the default gateway",
        "validator": auxiliar.validate_ip,

        "mode": "global_config",

        "render": "value",
        "descriptor": "ip default-gateway"
    },


    # --------------------------------------------------------
    # PC IP
    # --------------------------------------------------------

    "ip": {
        "question": "Write the IP address",
        "validator": auxiliar.validate_ip,

        "mode": None,
        "render": None
    },


    # --------------------------------------------------------
    # PC MASK
    # --------------------------------------------------------

    "mask": {
        "question": "Write the subnet mask",
        "validator": auxiliar.validate_ip,

        "mode": None,
        "render": None
    },


    # --------------------------------------------------------
    # PC DNS
    # --------------------------------------------------------

    "dns": {
        "question": "Write the DNS server",
        "validator": auxiliar.validate_ip,

        "mode": None,
        "render": None
    }
}


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
        render_multiple
}


# ============================================================
# SECTION DEFINITIONS
# ============================================================

SECTION_FIELDS = {

    "basic": {

        "pc": [
            "hostname",
            "ip",
            "mask",
            "gateway",
            "dns"
        ],

        "switch": [
            "hostname",
            "password_encryption",
            "gateway",
            "banner",
            "dns_lookup",
            "console_password",
            "vty_password",
            "privilege_password"
        ],

        "router": [
            "hostname",
            "password_encryption",
            "banner",
            "dns_lookup",
            "console_password",
            "vty_password",
            "privilege_password"
        ]
    },


    "security": {

        "pc": [],

        "switch": [],

        "router": []
    },


    "interfaces": {

        "pc": [],

        "switch": [],

        "router": []
    }
}


# ============================================================
# DEVICE SECTIONS
# ============================================================

DEVICE_SECTIONS = {

    "pc": [
        "basic"
    ],

    "switch": [
        "basic",
        "security",
        "interfaces"
    ],

    "router": [
        "basic",
        "security",
        "interfaces"
    ]
}


# ============================================================
# DEVICE CREATION
# ============================================================

def crear_device(device_type):

    device = {
        "type": device_type
    }

    for section in DEVICE_SECTIONS[device_type]:

        for field in SECTION_FIELDS[section][device_type]:

            device[field] = None

    return device


def crear_switch():
    return crear_device("switch")


def crear_router():
    return crear_device("router")


def crear_pc():
    return crear_device("pc")


# ============================================================
# SECTION FIELDS
# ============================================================

def get_section_fields(device, section):

    return SECTION_FIELDS[
        section
    ][
        device["type"]
    ]


# ============================================================
# SETUP SECTION
# ============================================================

def setup_section(device, section):

    temp_device = copy.deepcopy(device)

    fields = get_section_fields(
        temp_device,
        section
    )

    for field_name in fields:

        field = FIELD_DEFINITIONS[field_name]

        validator = field["validator"]

        result = validator(
            field["question"],
            temp_device[field_name]
        )


        # ----------------------------------------------------
        # CANCEL
        # ----------------------------------------------------

        if result is auxiliar.CANCEL:
            return auxiliar.CANCEL


        # ----------------------------------------------------
        # SKIP
        # ----------------------------------------------------

        if result is auxiliar.SKIP:
            continue


        # ----------------------------------------------------
        # TEMPORARY VALUE
        # ----------------------------------------------------

        temp_device[field_name] = result


    return temp_device


# ============================================================
# SECTION FUNCTIONS
# ============================================================

def basic_setup(device):

    return setup_section(
        device,
        "basic"
    )


def security_setup(device):

    return setup_section(
        device,
        "security"
    )


def interfaces_setup(device):

    return setup_section(
        device,
        "interfaces"
    )


# ============================================================
# SECTION DISPATCH
# ============================================================

SECTION_SETUP_FUNCTIONS = {

    "basic": basic_setup,
    "security": security_setup,
    "interfaces": interfaces_setup
}


# ============================================================
# RENDER FIELD
# ============================================================

def render_field(field_name, value):

    if value is None:
        return []

    field = FIELD_DEFINITIONS[field_name]

    render_type = field["render"]

    if render_type is None:
        return []

    render_function = RENDER_FUNCTIONS[
        render_type
    ]

    return render_function(
        field,
        value
    )


# ============================================================
# BUILD PLAN
# ============================================================
#
# Esta función NO imprime.
#
# Devuelve:
#
# {
#     "global_config": [
#         ...
#     ],
#
#     "line_console": [
#         ...
#     ],
#
#     "line_vty": [
#         ...
#     ]
# }
#
# ============================================================

def build_plan(device):

    plan = {}

    for field_name, value in device.items():

        if field_name == "type":
            continue

        if value is None:
            continue

        field = FIELD_DEFINITIONS[field_name]

        mode = field["mode"]

        if mode is None:
            continue

        commands = render_field(
            field_name,
            value
        )

        if not commands:
            continue

        if mode not in plan:
            plan[mode] = []

        plan[mode].extend(commands)

    return plan


# ============================================================
# MODE COMMANDS
# ============================================================
#
# Estos son los comandos que se usan para entrar a cada
# contexto de configuración.
#
# ============================================================

MODE_COMMANDS = {

    "global_config": {
        "enter": "configure terminal",
        "parent": None
    },

    "line_console": {
        "enter": "line console 0",
        "parent": "global_config"
    },

    "line_vty": {
        "enter": "line vty 0 15",
        "parent": "global_config"
    }
}


# ============================================================
# PRINT PLAN
# ============================================================
INDENT = 1

def print_plan(plan):
    print()
    print("-" * 60)
    print("IOS CONFIGURATION PLAN")
    print("-" * 60)

    print("enable")

    for mode, commands in plan.items():

        # Calcular profundidad del modo
        depth = 1
        current = mode

        while MODE_COMMANDS[current]["parent"] is not None:
            depth += 1
            current = MODE_COMMANDS[current]["parent"]

        # El comando que entra al modo queda en su profundidad
        father_indent = " " * (depth * INDENT)

        # Los comandos dentro del modo quedan un nivel más abajo
        child_indent = " " * ((depth + 1) * INDENT)

        print(f'{father_indent}{MODE_COMMANDS[mode]["enter"]}')

        for command in commands:
            print(f"{child_indent}{command}")

        if depth >0:
            print(f"{child_indent}exit")

    print("end")
    print("write memory")

    print("-" * 60)
    print()

# ============================================================
# SHOW DEVICE
# ============================================================

def show_device(device):

    print()
    print("-" * 60)
    print("CURRENT DEVICE")
    print("-" * 60)

    print(f"type: {device['type']}")

    for field, value in device.items():

        if field == "type":
            continue

        if value is None:
            print(
                f"{field}: not configured"
            )
        else:
            print(
                f"{field}: {value}"
            )

    print("-" * 60)
    print()


# ============================================================
# CHOOSE DEVICE
# ============================================================

def choose_device():

    devices = [
        "pc",
        "switch",
        "router"
    ]

    while True:

        auxiliar.show_options(
            devices
        )

        result = auxiliar.validate_number(
            devices
        )

        if result == -1:
            return None

        return crear_device(
            devices[result - 1]
        )


# ============================================================
# CATEGORIES SETUP
# ============================================================

def categories_setup():

    auxiliar.greeting_text(
        "Categories Setup"
    )

    device = choose_device()

    if device is None:
        return


    sections = DEVICE_SECTIONS[
        device["type"]
    ]


    while True:

        print()
        print(
            f"Device type: {device['type']}"
        )

        auxiliar.show_options(
            sections
        )

        result = auxiliar.validate_number(
            sections
        )

        if result == -1:
            return


        section = sections[
            result - 1
        ]

        setup_function = SECTION_SETUP_FUNCTIONS[
            section
        ]


        new_device = setup_function(
            device
        )


        if new_device is auxiliar.CANCEL:

            print()
            print(
                f"{section.capitalize()} "
                "setup cancelled."
            )

            continue


        device = new_device


        print()
        print(
            f"{section.capitalize()} "
            "setup completed."
        )

        show_device(device)


        # ----------------------------------------------------
        # BUILD PLAN
        # ----------------------------------------------------

        plan = build_plan(
            device
        )


        # ----------------------------------------------------
        # PRINT PLAN
        # ----------------------------------------------------

        print_plan(
            plan
        )


# ============================================================
# GUIDED SETUP
# ============================================================

def guided_setup():

    auxiliar.greeting_text(
        "Guided Setup"
    )

    pass


# ============================================================
# MAIN MENU
# ============================================================

def show_main_menu():

    auxiliar.greeting_text(
        "LAZY NETWORK SETUP"
    )

    options = [
        "Guided Setup",
        "Categories Setup"
    ]


    MAIN_MENU_FUNCTIONS = {

        "Guided Setup":
            guided_setup,

        "Categories Setup":
            categories_setup
    }


    while True:

        print(
            f"{' Welcome to the main menu ':-^60}"
        )

        auxiliar.show_options(
            options
        )

        result = auxiliar.validate_number(
            options
        )

        if result == -1:
            return


        option = options[
            result - 1
        ]

        MAIN_MENU_FUNCTIONS[
            option
        ]()


# ============================================================
# MAIN
# ============================================================

def main():

    show_main_menu()


if __name__ == "__main__":
    main()
