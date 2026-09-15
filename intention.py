import copy, auxiliar, catalog


# ============================================================
# DEVICE CREATION
# ============================================================

def crear_device(device_type):

    device = {
        "type": device_type
    }

    for section in catalog.DEVICE_SECTIONS[device_type]:

        for field in catalog.SECTION_FIELDS[section][device_type]:

            device[field] = None

    # las interfaces y las vlans no son campos planos:
    # son listas propias que se llenan con sus sub-loops

    if device_type in ("switch", "router"):
        device["interfaces"] = []

    if device_type == "switch":
        device["vlans"] = []

    return device

# ============================================================
# SETUP SECTION
# ============================================================

def setup_section(device, section):

    temp_device = copy.deepcopy(device)

    fields = catalog.get_section_fields(
        temp_device,
        section
    )

    for field_name in fields:

        field = catalog.resolve_field(field_name, temp_device["type"])

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

    # las VLANs primero: asi al cargar un puerto access ya
    # existen los IDs a los que se lo puede asignar

    if device["type"] == "switch":
        device = vlans_setup(device)

    device = interfaces_loop(device)

    return device


# ============================================================
# VLANS SETUP
# ============================================================
#
# Las VLANs viven en device["vlans"] como una lista de dicts:
#
#     [{"id": 10, "name": "VENTAS"}, {"id": 30, "name": None}]
#
# El name es opcional: build_plan ya contempla que sea None y
# emite igual el "vlan N", que es la creacion en si.
#
# ============================================================

def vlan_label(vlan):

    if vlan["name"]:
        return f"VLAN {vlan['id']} - {vlan['name']}"

    return f"VLAN {vlan['id']}"


def show_vlans(vlans):

    print()
    print("-" * 60)
    print("VLANS")
    print("-" * 60)

    if not vlans:
        print("No VLANs configured.")
    else:
        # desde 1, igual que show_options (el 0 es cancelar)
        for i, vlan in enumerate(vlans, start=1):
            print(f"{i}. {vlan_label(vlan)}")

    print("-" * 60)


def find_vlan(vlans, vlan_id):

    for i, vlan in enumerate(vlans):

        if vlan["id"] == vlan_id:
            return i

    return None


def choose_vlan(vlans):

    if not vlans:
        print()
        print("No VLANs configured.")
        return None

    labels = [vlan_label(vlan) for vlan in vlans]

    auxiliar.show_options(labels)

    result = auxiliar.validate_number(labels)

    if result == -1:
        return None

    return result - 1


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

def ask_vlan(current=None):

    current_id = current["id"] if current else None
    current_name = current["name"] if current else None

    # ----------------------------------------------------
    # ID
    # ----------------------------------------------------

    result = auxiliar.validate_vlan_id(
        catalog.FIELD_DEFINITIONS["vlan"]["question"],
        current_id
    )

    if result is auxiliar.CANCEL:
        return auxiliar.CANCEL

    if result is auxiliar.SKIP:

        # VLAN nueva: sin ID no hay nada que crear
        if current_id is None:
            return auxiliar.CANCEL

        vlan_id = current_id

    else:
        vlan_id = result

    # ----------------------------------------------------
    # NAME (opcional)
    # ----------------------------------------------------
    if vlan_id == 1:
        return {
            "id": vlan_id,
            "name": None
        }

    result = auxiliar.validate_optional_string(
        catalog.FIELD_DEFINITIONS["vlan_name"]["question"],
        current_name
    )

    if result is auxiliar.CANCEL:
        return auxiliar.CANCEL

    if result is auxiliar.SKIP:
        vlan_name = current_name
    else:
        vlan_name = result

    return {
        "id": vlan_id,
        "name": vlan_name
    }


# ============================================================
# VLANS LOOP
# ============================================================
#
# A diferencia de setup_section, cancelar aca aborta solo la
# VLAN en curso, no todo lo cargado antes. El 0 del menu
# confirma y devuelve.
#
# ============================================================

def vlans_setup(device):

    temp_device = copy.deepcopy(device)

    options = [
        "Add VLAN",
        "Edit VLAN",
        "Remove VLAN"
    ]

    while True:

        show_vlans(temp_device["vlans"])

        auxiliar.show_options(options)

        result = auxiliar.validate_number(options)

        if result == -1:
            return temp_device

        option = options[result - 1]

        # ----------------------------------------------------
        # ADD
        # ----------------------------------------------------

        if option == "Add VLAN":

            vlan = ask_vlan()

            if vlan is auxiliar.CANCEL:
                continue

            if find_vlan(temp_device["vlans"], vlan["id"]) is not None:
                print()
                print(f"VLAN {vlan['id']} already exists. Edit it instead.")
                continue

            if find_vlan_by_name(temp_device["vlans"], vlan["name"]) is not None:
                print()
                print(f"VLAN with name '{vlan['name']}' already exists. Edit it instead.")
                continue

            temp_device["vlans"].append(vlan)

        # ----------------------------------------------------
        # EDIT
        # ----------------------------------------------------

        elif option == "Edit VLAN":

            index = choose_vlan(temp_device["vlans"])

            if index is None:
                continue

            vlan = ask_vlan(temp_device["vlans"][index])

            if vlan is auxiliar.CANCEL:
                continue

            duplicate = find_vlan_by_name(temp_device["vlans"], vlan["name"])

            if duplicate is not None and duplicate != index:
                print()
                print(f"VLAN name '{vlan['name']}' already in use.")
                continue

            temp_device["vlans"][index] = vlan

        # ----------------------------------------------------
        # REMOVE
        # ----------------------------------------------------

        elif option == "Remove VLAN":

            index = choose_vlan(temp_device["vlans"])

            if index is None:
                continue

            removed = temp_device["vlans"].pop(index)

            print()
            print(f"{vlan_label(removed)} removed.")

def find_vlan_by_name(vlans, name):

    if not name:
        return None

    for i, vlan in enumerate(vlans):
        if vlan["name"] == name:
            return i

    return None

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
# El rol decide que campos se piden (INTERFACE_ROLES) y en que
# orden se renderizan. El nombre decide si build_plan usa
# "interface" o "interface range".
#
# ============================================================

def interface_label(interface):

    role = catalog.INTERFACE_ROLES[interface["role"]]["label"]

    return f"{interface['name']} ({role})"


def show_interfaces(interfaces):

    print()
    print("-" * 60)
    print("INTERFACES")
    print("-" * 60)

    if not interfaces:
        print("No interfaces configured.")
    else:
        for i, interface in enumerate(interfaces, start=1):
            print(f"{i}. {interface_label(interface)}")

    print("-" * 60)


def find_interface(interfaces, name):

    for i, interface in enumerate(interfaces):

        if interface["name"] == name:
            return i

    return None


def choose_interface(interfaces):

    if not interfaces:
        print()
        print("No interfaces configured.")
        return None

    labels = [interface_label(i) for i in interfaces]

    auxiliar.show_options(labels)

    result = auxiliar.validate_number(labels)

    if result == -1:
        return None

    return result - 1


# ============================================================
# ROLES
# ============================================================

def get_roles(device_type):

    return [
        name
        for name, role in catalog.INTERFACE_ROLES.items()
        if device_type in role["device_types"]
    ]


def choose_role(device_type, current=None):

    roles = get_roles(device_type)

    if not roles:
        print()
        print(f"No interface roles available for '{device_type}' yet.")
        return None

    labels = [catalog.INTERFACE_ROLES[name]["label"] for name in roles]

    print()

    if current is None:
        print("Choose the interface role")
    else:
        print(f"Choose the interface role [{catalog.INTERFACE_ROLES[current]['label']}]")

    auxiliar.show_options(labels)

    result = auxiliar.validate_number(labels)

    if result == -1:
        return None

    return roles[result - 1]


# ============================================================
# ASK INTERFACE FIELDS
# ============================================================
#
# Es setup_section pero operando sobre el dict de una interfaz
# en vez de sobre el device. Los campos y su orden salen de
# INTERFACE_ROLES[role]["ask_fields"].
#
# ============================================================

def ask_interface_fields(interface, device_type):

    role = catalog.INTERFACE_ROLES[interface["role"]]

    for field_name in role["ask_fields"]:

        field = catalog.resolve_field(field_name, device_type)

        validator = field["validator"]

        result = validator(
            field["question"],
            interface.get(field_name)
        )

        if result is auxiliar.CANCEL:
            return auxiliar.CANCEL

        if result is auxiliar.SKIP:
            continue

        interface[field_name] = result

    return interface


# ============================================================
# ASK INTERFACE
# ============================================================
#
# Devuelve un dict nuevo o auxiliar.CANCEL. No muta el que
# recibe (mismo motivo que ask_vlan).
#
# ============================================================

def ask_interface(device_type, current=None):

    current_name = current["name"] if current else None
    current_role = current["role"] if current else None

    # ----------------------------------------------------
        # ROLE
        # ----------------------------------------------------
        #
        # Va primero: define contra que patron se valida el
        # nombre en el paso siguiente.

    role = choose_role(device_type, current_role)

    if role is None:

        if current_role is None:
            return auxiliar.CANCEL

        role = current_role

    role_def = catalog.INTERFACE_ROLES[role]

    # ----------------------------------------------------
    # NAME
    # ----------------------------------------------------

    result = auxiliar.validate_interface_name(
        f"Write the interface name (e.g. {role_def['name_hint']})",
        current_name,
        pattern=role_def["name_pattern"],
        hint=role_def["name_hint"]
    )

    if result is auxiliar.CANCEL:
        return auxiliar.CANCEL

    if result is auxiliar.SKIP:

        if current_name is None:
            return auxiliar.CANCEL

        name = current_name

    else:
        name = result

    # ----------------------------------------------------
    # FIELDS
    # ----------------------------------------------------
    #
    # Si el rol cambio, los campos del rol viejo no se
    # arrastran: build_interface_commands los ignoraria, pero
    # quedarian en el dict confundiendo a show_device.

    interface = {"name": name, "role": role}

    if current and current_role == role:
        for field_name in catalog.INTERFACE_ROLES[role]["ask_fields"]:
            if field_name in current:
                interface[field_name] = current[field_name]

    result = ask_interface_fields(interface, device_type)

    if result is auxiliar.CANCEL:
        return auxiliar.CANCEL

    return result


# ============================================================
# INTERFACES LOOP
# ============================================================

def interfaces_loop(device):

    temp_device = copy.deepcopy(device)

    options = [
        "Add interface",
        "Edit interface",
        "Remove interface"
    ]

    while True:

        show_interfaces(temp_device["interfaces"])

        auxiliar.show_options(options)

        result = auxiliar.validate_number(options)

        if result == -1:
            return temp_device

        option = options[result - 1]

        # ----------------------------------------------------
        # ADD
        # ----------------------------------------------------

        if option == "Add interface":

            interface = ask_interface(temp_device["type"])

            if interface is auxiliar.CANCEL:
                continue

            if find_interface(temp_device["interfaces"], interface["name"]) is not None:
                print()
                print(
                    f"{interface['name']} already exists. Edit it instead."
                )
                continue

            temp_device["interfaces"].append(interface)

        # ----------------------------------------------------
        # EDIT
        # ----------------------------------------------------

        elif option == "Edit interface":

            index = choose_interface(temp_device["interfaces"])

            if index is None:
                continue

            interface = ask_interface(
                temp_device["type"],
                temp_device["interfaces"][index]
            )

            if interface is auxiliar.CANCEL:
                continue

            temp_device["interfaces"][index] = interface

        # ----------------------------------------------------
        # REMOVE
        # ----------------------------------------------------

        elif option == "Remove interface":

            index = choose_interface(temp_device["interfaces"])

            if index is None:
                continue

            removed = temp_device["interfaces"].pop(index)

            print()
            print(f"{interface_label(removed)} removed.")


# ============================================================
# SECTION DISPATCH
# ============================================================

SECTION_SETUP_FUNCTIONS = {

    "basic": basic_setup,
    "security": security_setup,
    "interfaces": interfaces_setup
}
