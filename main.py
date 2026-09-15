import os

import auxiliar
import pyperclip

import catalog
import intention
import serialize
import lint

from plan import build_plan


OUTPUT_DIR = "configs"


# ============================================================
# INTERFACE NAME PATTERNS
# ============================================================
#
# Cada rol declara que forma puede tener el nombre de su
# interfaz. Sin esto se puede elegir el rol "svi" y tipear
# "f0/1", que genera "ip address" en un puerto de capa 2 y
# el IOS lo rechaza.
#
# El lookahead negativo en _PORT evita que "vlan10" pase
# como puerto fisico.
# ============================================================


# ============================================================
# INTERFACE ROLES
# ============================================================

# ask_fields    -> que se le pregunta al usuario, en orden
# render_fields -> que comandos se emiten, en orden
#
# No son la misma lista: "ip address X Y" es UN comando que
# necesita DOS respuestas (ipv4 + mask_ipv4). El campo virtual
# ip_address los junta al renderizar.


# ============================================================
# CONFIG FILE
# ============================================================


# ============================================================
# BUILD CONFIG FILE
# ============================================================


# ============================================================
# SAVE CONFIG FILE
# ============================================================

def save_config_file(device, path=None):

    hostname = device.get("hostname") or device["type"]

    if path is None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        path = os.path.join(OUTPUT_DIR, f"{hostname}.txt")

    with open(path, "w", encoding="utf-8") as file:
        file.write(serialize.build_config_file(device))

    print(f"Config file saved -> {path}")
    return path

# ============================================================
# EXPORT PLAN
# ============================================================

def export_plan(device, plan):

    if not plan:
        return

    text = serialize.plan_to_text(plan)

    rt = auxiliar.validate_yes_no(
        "Copy the configuration to the clipboard?"
    )

    if rt is True:
        pyperclip.copy(text)
        print("Configuration copied to clipboard.")

    rt = auxiliar.validate_yes_no(
        "Save the configuration to a file?"
    )

    if rt is True:
        save_config_file(device)

        if device.get("crypto_key"):
            print(
                "Note: 'crypto key generate rsa' is not included "
                "in the config file. Run it manually after loading."
            )


# ============================================================
# FIELD DEFINITIONS
# ============================================================


# ============================================================
# RENDERERS
# ============================================================


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


# ============================================================
# RENDER DISPATCH
# ============================================================


# ============================================================
# SECTION DEFINITIONS
# ============================================================


# ============================================================
# DEVICE SECTIONS
# ============================================================


# ============================================================
# DEVICE CREATION
# ============================================================


# ============================================================
# SECTION FIELDS
# ============================================================


# ============================================================
# RESOLVE FIELD
# ============================================================


# ============================================================
# SETUP SECTION
# ============================================================


# ============================================================
# SECTION FUNCTIONS
# ============================================================


# ============================================================
# VLANS SETUP
# ============================================================
#
# Las VLANs viven en device["vlans"] como una lista de dicts:
#
#     [{"id": 10, "name": "VENTAS"}, {"id": 30, "name": None}]
#
# El name es opcional: plan.build_plan ya contempla que sea None y
# emite igual el "vlan N", que es la creacion en si.
#
# ============================================================


# ============================================================
# ASK VLAN
# ============================================================
#
# Devuelve un dict nuevo o auxiliar.CANCEL.
#
# NO muta el dict que recibe: cuando se edita, current es el
# dict real de la lista, y un cancel a mitad de camino lo
# dejaria a medio escribir.
#
# ============================================================


# ============================================================
# VLANS LOOP
# ============================================================
#
# A diferencia de setup_section, cancelar aca aborta solo la
# VLAN en curso, no todo lo cargado antes. El 0 del menu
# confirma y devuelve.
#
# ============================================================


# ============================================================
# INTERFACES SETUP
# ============================================================
#
# Las interfaces viven en device["interfaces"] como una lista
# de dicts:
#
#     [{"name": "fa0/1-12", "role": "access", "access_vlan": 10},
#      {"name": "g0/1", "role": "trunk", "trunk_allowed": "1,10,30"}]
#
# El rol decide que campos se piden (catalog.INTERFACE_ROLES) y en que
# orden se renderizan. El nombre decide si plan.build_plan usa
# "interface" o "interface range".
#
# ============================================================


# ============================================================
# ROLES
# ============================================================


# ============================================================
# ASK INTERFACE FIELDS
# ============================================================
#
# Es setup_section pero operando sobre el dict de una interfaz
# en vez de sobre el device. Los campos y su orden salen de
# catalog.INTERFACE_ROLES[role]["fields"].
#
# ============================================================


# ============================================================
# ASK INTERFACE
# ============================================================
#
# Devuelve un dict nuevo o auxiliar.CANCEL. No muta el que
# recibe (mismo motivo que ask_vlan).
#
# ============================================================


# ============================================================
# INTERFACES LOOP
# ============================================================


# ============================================================
# SECTION DISPATCH
# ============================================================


# ============================================================
# RENDER FIELD
# ============================================================


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


# ============================================================
# LINT RULES
# ============================================================
#
# Cada regla recibe el device y devuelve una lista de strings
# (vacia si no hay nada que decir). No modifican el device y
# no hacen I/O: se pueden testear con un device literal.
#
# Agregar una regla = escribir la funcion y sumarla a
# LINT_RULES. El motor no cambia.
# ============================================================


# ============================================================
# RUN RULES
# ============================================================
#
# Pura: device -> lista de advertencias. Sin prints.
# ============================================================


# ============================================================
# LINT DEVICE
# ============================================================
#
# Solo imprime. No bloquea, no pregunta y no modifica el
# device: el usuario puede tener motivos para ignorar una
# advertencia.
# ============================================================


# ============================================================
# MODE COMMANDS
# ============================================================
#
# Estos son los comandos que se usan para entrar a cada
# contexto de configuracion. Los que terminan en espacio
# esperan un "arg" que se concatena (interface, vlan).
#
# ============================================================


# ============================================================
# PLAN TO TEXT
# ============================================================


# ============================================================
# PRINT PLAN
# ============================================================


def print_plan(plan):

    if not plan:
        print()
        print("Nothing to configure")
        print()
        return

    print()
    print("-" * 60)
    print("IOS CONFIGURATION PLAN")
    print("-" * 60)
    print(serialize.plan_to_text(plan))
    print("-" * 60)
    print()

def print_pc_plan(device):

    print()
    print("-" * 60)
    print("PC — Desktop > IP Configuration")
    print("-" * 60)

    for field_name in catalog.SECTION_FIELDS["basic"]["pc"]:

        value = device.get(field_name)

        if value is None:
            continue

        field = catalog.resolve_field(field_name, device["type"])

        label = field.get("label")

        if label is None:
            continue

        print(f"  {label:<26}{value}")

    print("-" * 60)
    print()

# ============================================================
# PLAN PRINT DISPATCH
# ============================================================

def print_ios_plan(device, plan):
    print_plan(plan)


def print_pc_plan_wrapper(device, plan):
    print_pc_plan(device)


PLAN_PRINT_FUNCTIONS = {
    "pc": print_pc_plan_wrapper,
    "switch": print_ios_plan,
    "router": print_ios_plan
}


def choose_plan(device, plan):
    print_function = PLAN_PRINT_FUNCTIONS[device["type"]]
    print_function(device, plan)

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

        # las listas se imprimen aparte: el repr crudo de una
        # lista de dicts es ilegible

        if field == "vlans":

            if not value:
                print("vlans: none")
            else:
                print("vlans:")
                for vlan in value:
                    print(f"  - {intention.vlan_label(vlan)}")

            continue

        if field == "interfaces":

            if not value:
                print("interfaces: none")
            else:
                print("interfaces:")
                for interface in value:
                    role = catalog.INTERFACE_ROLES[interface["role"]]["label"]
                    print(f"  - {interface['name']} ({role})")

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

    auxiliar.show_options(
        devices
    )

    result = auxiliar.validate_number(
        devices
    )

    if result == -1:
        return None

    return intention.crear_device(
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


    sections = catalog.DEVICE_SECTIONS[
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

        setup_function = intention.SECTION_SETUP_FUNCTIONS[
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
        # LINT DEVICE
        # ----------------------------------------------------

        lint.lint_device(device)

        # ----------------------------------------------------
        # PRINT PLAN
        # ----------------------------------------------------

        choose_plan(device, plan)

        # ----------------------------------------------------
        # EXPORT PLAN
        # ----------------------------------------------------

        export_plan(device, plan)


# ============================================================
# GUIDED SETUP
# ============================================================

def guided_setup():

    auxiliar.greeting_text(
        "Guided Setup"
    )

    device = choose_device()

    if device is None:
        return

    sections = catalog.DEVICE_SECTIONS[
        device["type"]
    ]

    print(
        f"Device type: {device['type']}"
    )

    for section in sections:

        print()

        setup_function = intention.SECTION_SETUP_FUNCTIONS[
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
    # LINT DEVICE
    # ----------------------------------------------------

    lint.lint_device(device)

    # ----------------------------------------------------
    # PRINT PLAN
    # ----------------------------------------------------

    choose_plan(device, plan)

    # ----------------------------------------------------
    # EXPORT PLAN
    # ----------------------------------------------------

    export_plan(device, plan)


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
# TEST PLAN
# ============================================================
#
# Device armado a mano para probar el rendering sin tener que
# tipear 20 respuestas. Borrar cuando este el loop de
# interfaces.
#
# ============================================================

def test_plan():

    device = {
        "type": "switch",
        "hostname": "S1",
        "console_password": "cisco",
        "vlans": [
            {"id": 10, "name": "VENTAS"},
            {"id": 30, "name": "ADMIN"}
        ],
        "interfaces": [
            {
                "name": "fa0/1-12",
                "role": "access",
                "access_vlan": 10,
                "description": "PCs ventas",
                "shutdown": False
            },
            {
                "name": "g0/1",
                "role": "trunk",
                "trunk_allowed": "1,10,30",
                "trunk_native": 1
            }
        ]
    }

    print_plan(build_plan(device))

    print("-" * 60)
    print("CONFIG FILE")
    print("-" * 60)
    print(serialize.build_config_file(device))
    print("-" * 60)


# ============================================================
# MAIN
# ============================================================

def main():

    # test_plan()
    show_main_menu()


if __name__ == "__main__":
    main()
