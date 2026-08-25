import copy
import auxiliar


# ============================================================
# FIELD DEFINITIONS
# ============================================================
#
# Cada campo se define UNA sola vez.
#
# Las secciones y los tipos de dispositivo solamente hacen
# referencia a estos nombres.
#
# Si mañana cambiamos el texto de "banner", lo cambiamos acá
# una sola vez.
#


FIELD_DEFINITIONS = {

    # -------------------------
    # Common Cisco fields
    # -------------------------

    "hostname": {
        "question": "Write the hostname",
        "validator": auxiliar.validate_hostname
    },

    "password_encryption": {
        "question": "Enable service password-encryption?",
        "validator": auxiliar.validate_yes_no
    },

    "banner": {
        "question": "Write the banner",
        "validator": auxiliar.validate_optional_string
    },

    "dns_lookup": {
        "question": (
            "Enable DNS lookup? "
            "(yes = the device performs DNS lookups)"
        ),
        "validator": auxiliar.validate_yes_no
    },

    "console_password": {
        "question": "Write the console password",
        "validator": auxiliar.validate_optional_string
    },

    "vty_password": {
        "question": "Write the VTY password",
        "validator": auxiliar.validate_optional_string
    },

    "privilege_password": {
        "question": "Write the privilege password",
        "validator": auxiliar.validate_optional_string
    },


    # -------------------------
    # Network fields
    # -------------------------

    "ip": {
        "question": "Write the IP address",
        "validator": auxiliar.validate_ip
    },

    "mask": {
        "question": "Write the subnet mask",
        "validator": auxiliar.validate_ip
    },

    "gateway": {
        "question": "Write the default gateway",
        "validator": auxiliar.validate_ip
    },

    "dns": {
        "question": "Write the DNS server",
        "validator": auxiliar.validate_ip
    }
}


# ============================================================
# SECTION DEFINITIONS
# ============================================================
#
# Las secciones NO contienen descriptores repetidos.
# Solamente dicen qué campos pertenecen a cada sección.
#


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
# DEVICE TYPES
# ============================================================
#
# Esto define qué secciones tiene cada tipo.
#
# No usamos "if type == pc / else".
#


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
#
# El device se construye a partir de SECTION_FIELDS.
#
# Ya NO existe una lista manual de keys en crear_switch(),
# crear_router() o crear_pc().
#


def crear_device(device_type):

    device = {
        "type": device_type
    }

    sections = DEVICE_SECTIONS[device_type]

    for section in sections:

        fields = SECTION_FIELDS[section][device_type]

        for field in fields:
            device[field] = None

    return device


def crear_switch():
    return crear_device("switch")


def crear_router():
    return crear_device("router")


def crear_pc():
    return crear_device("pc")


# ============================================================
# GET SECTION FIELDS
# ============================================================

def get_section_fields(device, section):

    device_type = device["type"]

    return SECTION_FIELDS[section][device_type]


# ============================================================
# SETUP SECTION
# ============================================================
#
# Una sección trabaja sobre una copia.
#
# SKIP:
#     no modifica el campo.
#
# CANCEL:
#     descarta TODA la copia.
#
# Valor:
#     modifica la copia.
#
# Al terminar:
#     devuelve la copia para hacer commit.
#


def setup_section(device, section):

    temp_device = copy.deepcopy(device)

    fields = get_section_fields(
        temp_device,
        section
    )

    for field in fields:

        definition = FIELD_DEFINITIONS[field]

        question = definition["question"]
        validator = definition["validator"]

        current = temp_device[field]

        result = validator(
            question,
            current
        )

        # -------------------------
        # Cancel entire section
        # -------------------------

        if result is auxiliar.CANCEL:
            return auxiliar.CANCEL

        # -------------------------
        # Keep current value
        # -------------------------

        if result is auxiliar.SKIP:
            continue

        # -------------------------
        # Set new value
        # -------------------------

        temp_device[field] = result

    return temp_device


# ============================================================
# SECTION SETUPS
# ============================================================

def basic_setup(device):
    return setup_section(device, "basic")


def security_setup(device):
    return setup_section(device, "security")


def interfaces_setup(device):
    return setup_section(device, "interfaces")


# ============================================================
# SECTION DISPATCH
# ============================================================
#
# No hay case 1 / case 2 / case 3.
#
# La relación "opción -> función" está en este diccionario.
#


SECTION_SETUP_FUNCTIONS = {
    "basic": basic_setup,
    "security": security_setup,
    "interfaces": interfaces_setup
}


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

        auxiliar.show_options(devices)

        result = auxiliar.validate_number(devices)

        if result == -1:
            return None

        device_type = devices[result - 1]

        return crear_device(device_type)


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
            print(f"{field}: not configured")
        else:
            print(f"{field}: {value}")

    print("-" * 60)
    print()


# ============================================================
# CATEGORIES SETUP
# ============================================================

def categories_setup():

    auxiliar.greeting_text("Categories Setup")

    device = choose_device()

    if device is None:
        return


    # ---------------------------------
    # Only sections available for
    # this device type
    # ---------------------------------

    sections = DEVICE_SECTIONS[device["type"]]


    while True:

        print()
        print(f"Device type: {device['type']}")

        auxiliar.show_options(sections)

        result = auxiliar.validate_number(sections)

        if result == -1:
            return


        # ---------------------------------
        # Convert menu position into
        # section name
        # ---------------------------------

        section = sections[result - 1]


        # ---------------------------------
        # Find function
        # ---------------------------------

        setup_function = SECTION_SETUP_FUNCTIONS[section]


        # ---------------------------------
        # Execute section
        # ---------------------------------

        new_device = setup_function(device)


        # ---------------------------------
        # Cancel
        # ---------------------------------

        if new_device is auxiliar.CANCEL:

            print()
            print(f"{section.capitalize()} setup cancelled.")

            continue


        # ---------------------------------
        # Commit
        # ---------------------------------

        device = new_device

        print()
        print(f"{section.capitalize()} setup completed.")

        show_device(device)


# ============================================================
# GUIDED SETUP
# ============================================================

def guided_setup():

    auxiliar.greeting_text("Guided Setup")

    # Todavía no implementado.
    pass


# ============================================================
# MAIN MENU
# ============================================================

def show_main_menu():

    auxiliar.greeting_text("LAZY NETWORK SETUP")

    options = [
        "Guided Setup",
        "Categories Setup"
    ]


    MAIN_MENU_FUNCTIONS = {
        "Guided Setup": guided_setup,
        "Categories Setup": categories_setup
    }


    while True:

        print(f"{' Welcome to the main menu ':-^60}")

        auxiliar.show_options(options)

        result = auxiliar.validate_number(options)

        if result == -1:
            return


        option = options[result - 1]

        function = MAIN_MENU_FUNCTIONS[option]

        function()


# ============================================================
# MAIN
# ============================================================

def main():
    show_main_menu()


if __name__ == "__main__":
    main()
