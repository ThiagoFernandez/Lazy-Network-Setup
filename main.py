import copy
import re
import auxiliar
import pyperclip
import os

OUTPUT_DIR = "configs"

INDENT = 1

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

_PORT       = r"(?![Vv]lan)[A-Za-z]+[0-9]+(?:/[0-9]+)*"
_PORT_RANGE = _PORT + r"-[0-9]+"
_SUBIF      = _PORT + r"\.[0-9]+"
_SVI        = r"[Vv]lan ?[0-9]{1,4}"

# ============================================================
# INTERFACE ROLES
# ============================================================

# ask_fields    -> que se le pregunta al usuario, en orden
# render_fields -> que comandos se emiten, en orden
#
# No son la misma lista: "ip address X Y" es UN comando que
# necesita DOS respuestas (ipv4 + mask_ipv4). El campo virtual
# ip_address los junta al renderizar.

INTERFACE_ROLES = {

"access": {
    "label": "Access port",
    "device_types": ["switch"],
    "name_pattern": f"{_PORT}|{_PORT_RANGE}",
    "name_hint": "g0/1 o fa0/1-12",
    "ask_fields": ["description", "access_vlan", "shutdown"],
    "render_fields": ["description", "access_vlan", "shutdown"]
},

"trunk": {
    "label": "Trunk port",
    "device_types": ["switch"],
    "name_pattern": f"{_PORT}|{_PORT_RANGE}",
    "name_hint": "g0/1 o fa0/1-12",
    "ask_fields": ["description", "trunk_allowed", "trunk_native", "shutdown"],
    "render_fields": ["description", "trunk_allowed", "trunk_native", "shutdown"]
},

"svi": {
    "label": "SVI (management)",
    "device_types": ["switch"],
    "name_pattern": _SVI,
    "name_hint": "vlan99",
    "ask_fields": ["description", "ipv4", "mask_ipv4", "shutdown"],
    "render_fields": ["description", "ip_address", "shutdown"]
},

# la encapsulacion va ANTES que la IP: es el orden en que
# el IOS las espera, y tenerlo aca hace imposible cruzar
# el numero de subinterfaz con el de la VLAN

"subinterface": {
    "label": "Subinterface (router-on-a-stick)",
    "device_types": ["router"],
    "name_pattern": _SUBIF,
    "name_hint": "g0/0/1.10",
    "ask_fields": ["description", "encapsulation", "ipv4", "mask_ipv4"],
    "render_fields": ["description", "encapsulation", "ip_address"]
}
}

# ============================================================
# CONFIG FILE
# ============================================================

NOT_IN_CONFIG_FILE = {"crypto_key"} # opt

# ============================================================
# BUILD CONFIG FILE
# ============================================================

def build_config_file(device):

    filtered = {
        k: v for k, v in device.items()
        if k not in NOT_IN_CONFIG_FILE
    }

    plan = build_plan(filtered)
    lines = ["!"]

    for block in plan:

        if block["mode"] == CONFIG_FILE_ROOT:
            for command in block["commands"]:
                lines.append(command)
        else:
            enter = MODE_COMMANDS[block["mode"]]["enter"]

            if block.get("arg"):
                enter = f"{enter}{block['arg']}"

            lines.append(enter)

            for command in block["commands"]:
                lines.append(f" {command}")

        lines.append("!")

    lines.append("end")

    return "\n".join(lines)

# ============================================================
# SAVE CONFIG FILE
# ============================================================

def save_config_file(device, path=None):

    hostname = device.get("hostname") or device["type"]

    if path is None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        path = os.path.join(OUTPUT_DIR, f"{hostname}.txt")

    with open(path, "w", encoding="utf-8") as file:
        file.write(build_config_file(device))

    print(f"Config file saved -> {path}")
    return path

# ============================================================
# EXPORT PLAN
# ============================================================

def export_plan(device, plan):

    if not plan:
        return

    text = plan_to_text(plan)

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

    "gateway_ipv6": {
        "question": "Write the default gateway(ipv6)",
        "validator": auxiliar.validate_ip,
        "label": "IPv6 Default Gateway",

        "targets": {
            "pc": {"mode": None, "render": None}
        }
    },


    "management_gateway_ipv4": {
        "question": "Write the IPv4 default gateway",
        "validator": auxiliar.validate_ip,
        "label": "IPv4 Default Gateway",

        "targets": {
            "pc": {
                "mode": None,
                "render": None
            },
            "switch": {
                "mode": "global_config",
                "render": "value",
                "descriptor": "ip default-gateway"
            }
        }
    },

    "default_route_ipv4": {
        "question": "Write the IPv4 default route next-hop",
        "validator": auxiliar.validate_ip,
        "label": "IPv4 Default Route",

        "targets": {
            "router": {
                "mode": "global_config",
                "render": "value",
                "descriptor": "ip route 0.0.0.0 0.0.0.0"
            }
        }
    },

    # --------------------------------------------------------
    # DOMAIN-NAME
    # --------------------------------------------------------

    "domain_name": {
        "question": "Write the domain name",
        "validator": auxiliar.validate_optional_string,

        "mode": "global_config",

        "render": "value",
        "descriptor": "ip domain-name"
    },


    # --------------------------------------------------------
    # CRYPTO-KEY
    # --------------------------------------------------------

    "crypto_key": { # este es complejo
        "question": (
            "Enable crypto key? "
        ),
        "validator": auxiliar.validate_yes_no,

        "mode": "global_config",

        "render": "boolean_enable",
        "descriptor": "crypto key generate rsa\n  1024" # I had to fix ts in a future cuz ts could lead to indentation bugs
    },


    # --------------------------------------------------------
    # USERNAME
    # --------------------------------------------------------

    "username": {
        "question": "Configure username and secret",
        "validator": auxiliar.validate_username,

        "mode": "global_config",

        "render": "structured_multiple",
        "commands": [
            "username {user} privilege 15 secret {secret}"
        ]
    },

    # --------------------------------------------------------
    # SSH-VERSION
    # --------------------------------------------------------

    "ssh_version": {
        "question": (
            "Enable ssh version 2?"
            "(yes = the device force ssh version 2)"
        ),
        "validator": auxiliar.validate_yes_no,

        "mode": "global_config",

        "render": "boolean_enable_disable",
        "descriptor": "ip ssh version 2"
    },

    # --------------------------------------------------------
    # MIN-LENGTH
    # --------------------------------------------------------

    "min_length": {
        "question": "Write the minimun length of the password",
        "validator": auxiliar.validate_number_v2,

        "mode": "global_config",

        "render": "value",
        "descriptor": "security passwords min-length"
    },


    # --------------------------------------------------------
    # LOGIN-BLOCK
    # --------------------------------------------------------

    "login_block": { # este tambien es complejo porque pide tiempo e intentos y en cuanto
        "question": (
            "Setup your login block?"
        ),
        "validator": auxiliar.validate_yes_no,

        "mode": "global_config",

        "render": "", # esto explota pero no lo agregue todavia
        "descriptor": "login block-for 30 attempts 2 within 120"
    },


    # --------------------------------------------------------
    # TRANSPORT-INPUT
    # --------------------------------------------------------

    "transport_input": {
        "question": (
            "Choose the transport input method"
        ),
        "validator": auxiliar.validate_transport,

        "mode": "line_vty",

        "render": "value",
        "descriptor": "transport input"
    },

    # --------------------------------------------------------
    # LOGIN-LOCAL
    # --------------------------------------------------------

    "login_local": {
        "question": (
            "Enable the login local?"
        ),
        "validator": auxiliar.validate_yes_no,

        "mode": "line_vty",

        "render": "boolean_enable_disable",
        "descriptor": "login local"
    },

    # --------------------------------------------------------
    # PC IP
    # --------------------------------------------------------

    # en switch y router estos dos NO se renderizan solos:
    # los consume el campo virtual ip_address

    "ipv4": {
        "question": "Write the IPv4 address",
        "validator": auxiliar.validate_ip,
        "label": "IPv4 Address",

        "targets": {
            "pc": {
                "mode": None,
                "render": None
            },
            "switch": {
                "mode": None,
                "render": None
            },
            "router": {
                "mode": None,
                "render": None
            }
        }
    },

    "ipv6": {
        "question": "Write the IPv6 address",
        "validator": auxiliar.validate_ip,
        "label": "IPv6 Address",

        "targets": {
            "pc": {
                "mode": None,
                "render": None
            }
        }
    },


    # --------------------------------------------------------
    # PC MASK
    # --------------------------------------------------------

    "mask_ipv4": {
        "question": "Write the IPv4 subnet mask",
        "validator": auxiliar.validate_ip,
        "label": "IPv4 Subnet Mask",

        "targets": {
            "pc": {
                "mode": None,
                "render": None
            },
            "switch": {
                "mode": None,
                "render": None
            },
            "router": {
                "mode": None,
                "render": None
            }
        }
    },


    # --------------------------------------------------------
    # IP ADDRESS (campo virtual)
    # --------------------------------------------------------
    #
    # No se pregunta: "requires" dice de que campos toma los
    # valores, y build_interface_commands le pasa un dict con
    # todos ellos en vez de un valor suelto.
    #
    # Solo aparece en render_fields, nunca en ask_fields.
    # --------------------------------------------------------

    "ip_address": {
        "requires": ["ipv4", "mask_ipv4"],

        "mode": "interface",

        "render": "template",
        "commands": [
            "ip address {ipv4} {mask_ipv4}"
        ]
    },


    "prefix": {
        "question": "Write the prefix",
        "validator": auxiliar.validate_prefix,
        "label": "Prefix",

        "targets": {
            "pc": {"mode": None, "render": None}
        }
    },


    # --------------------------------------------------------
    # PC LINK LOCAL (ipv6)
    # --------------------------------------------------------

    "link_local": {
        "question": "Write the link local address",
        "validator": auxiliar.validate_ip,
        "label": "IPv6 Link Local Address",

        "targets": {
            "pc": {"mode": None, "render": None}
        }
    },


    # --------------------------------------------------------
    # PC DNS
    # --------------------------------------------------------

    "dns": {
        "question": "Write the IP DNS server",
        "validator": auxiliar.validate_ip,
        "label": "IP DNS",

        "targets": {
            "pc": {
                "mode": None,
                "render": None
            },
            "switch": {
                "mode": "global_config",
                "render": "value",
                "descriptor": "ip name-server"
            },
            "router": {
                "mode": "global_config",
                "render": "value",
                "descriptor": "ip name-server"
            }
        }
    },

    "vlan": {
        "question": "Write the VLAN ID (1-4094)",
        "validator": auxiliar.validate_vlan_id,
        "label": "",

        "targets": {
            "pc": {
                "mode": None,
                "render": None
            },
            "switch": {
                "mode": "global_config",
                "render": "value",
                "descriptor": "vlan"
            },
            "router": {
                "mode": "global_config",
                "render": "value",
                "descriptor": "vlan"
            }
        }
    },


    # --------------------------------------------------------
    # INTERFACE FIELDS
    # --------------------------------------------------------

    "shutdown": {
        "question": "Shutdown the interface?",
        "validator": auxiliar.validate_yes_no,
        "label": "",

        "mode": "interface",

        "render": "boolean_enable_disable",
        "descriptor": "shutdown"
    },

    "description": {
        "question": "Interface description:",
        "validator": auxiliar.validate_optional_string,
        "label": "",

        "mode": "interface",

        "render": "value",
        "descriptor": "description"
    },

    "access_vlan": {
        "question": "Write the access VLAN ID",
        "validator": auxiliar.validate_vlan_id,

        "mode": "interface",

        "render": "multiple",
        "commands": [
            "switchport mode access",
            "switchport access vlan {value}"
        ]
    },

    "trunk_allowed": {
        "question": "Write the allowed VLANs (e.g. 1,10,30)",
        "validator": auxiliar.validate_vlan_list,

        "mode": "interface",

        "render": "multiple",
        "commands": [
            "switchport mode trunk",
            "switchport trunk allowed vlan {value}"
        ]
    },

    "trunk_native": {
        "question": "Write the native VLAN ID",
        "validator": auxiliar.validate_vlan_id,

        "mode": "interface",

        "render": "value",
        "descriptor": "switchport trunk native vlan"
    },

    # usado por el rol subinterface (router-on-a-stick)
    "encapsulation": {
        "question": "Write the VLAN ID for the encapsulation",
        "validator": auxiliar.validate_vlan_id,

        "mode": "interface",

        "render": "value",
        "descriptor": "encapsulation dot1Q"
    },


    # --------------------------------------------------------
    # VLAN FIELDS
    # --------------------------------------------------------

    "vlan_name": {
        "question": "Write the VLAN name",
        "validator": auxiliar.validate_optional_string,

        "mode": "vlan",

        "render": "value",
        "descriptor": "name"
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
# SECTION DEFINITIONS
# ============================================================

SECTION_FIELDS = {

    "basic": {

        "pc": [
            "ipv4",
            "mask_ipv4",
            "management_gateway_ipv4",
            "dns",
            "ipv6",
            "prefix",
            "link_local",
            "gateway_ipv6",

        ],

        "switch": [
            "hostname",
            "password_encryption",
            "management_gateway_ipv4",
            "banner",
            "dns_lookup",
            "console_password",
            "vty_password",
            "privilege_password"
        ],

        "router": [
            "hostname",
            "password_encryption",
            "default_route_ipv4",
            "banner",
            "dns_lookup",
            "min_length",
            "console_password",
            "vty_password",
            "privilege_password"
        ]
    },


    "security": {

        "pc": [],

        "switch": [
            "username",
            "domain_name",
            "crypto_key",
            "ssh_version",
            "login_local",
            "transport_input"
        ],

        "router": [
            "username",
            "domain_name",
            "crypto_key",
            "ssh_version",
            "login_local",
            "transport_input"
        ]
    },


    # las interfaces ya no se cargan como campos planos:
    # viven en device["interfaces"] y se piden con su propio loop
    "interfaces": {

        "pc": [],

        "switch": [
        ],

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

    # las interfaces y las vlans no son campos planos:
    # son listas propias que se llenan con sus sub-loops

    if device_type in ("switch", "router"):
        device["interfaces"] = []

    if device_type == "switch":
        device["vlans"] = []

    return device


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
# RESOLVE FIELD
# ============================================================

def resolve_field(field_name, device_type):

    field = FIELD_DEFINITIONS[field_name]

    if "targets" not in field:
        return field

    if not device_type:
        raise ValueError(f"Device type missing to resolve targets for field '{field_name}'")

    if device_type not in field["targets"]:
        raise KeyError(f"Target '{device_type}' not found for field '{field_name}'")

    resolved_field = field.copy()
    target_config = resolved_field.pop("targets")[device_type]
    resolved_field.update(target_config)

    return resolved_field


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

        field = resolve_field(field_name, temp_device["type"])

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
        FIELD_DEFINITIONS["vlan"]["question"],
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
        FIELD_DEFINITIONS["vlan_name"]["question"],
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

    role = INTERFACE_ROLES[interface["role"]]["label"]

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
        for name, role in INTERFACE_ROLES.items()
        if device_type in role["device_types"]
    ]


def choose_role(device_type, current=None):

    roles = get_roles(device_type)

    if not roles:
        print()
        print(f"No interface roles available for '{device_type}' yet.")
        return None

    labels = [INTERFACE_ROLES[name]["label"] for name in roles]

    print()

    if current is None:
        print("Choose the interface role")
    else:
        print(f"Choose the interface role [{INTERFACE_ROLES[current]['label']}]")

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
# INTERFACE_ROLES[role]["fields"].
#
# ============================================================

def ask_interface_fields(interface, device_type):

    role = INTERFACE_ROLES[interface["role"]]

    for field_name in role["ask_fields"]:

        field = resolve_field(field_name, device_type)

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

    role_def = INTERFACE_ROLES[role]

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
        for field_name in INTERFACE_ROLES[role]["ask_fields"]:
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

        field = resolve_field(field_name, device["type"])

        mode = field.get("mode")

        if mode is None:
            continue

        commands = render_field(field, value)

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
            field = resolve_field("vlan_name", device["type"])
            commands.extend(render_field(field, vlan["name"]))

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

    role = INTERFACE_ROLES[interface["role"]]

    commands = []

    for field_name in role["render_fields"]:

        field = resolve_field(field_name, device_type)

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

        commands.extend(render_field(field, value))

    return commands

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

def device_own_ips(device):

    # Todas las IPs que el dispositivo tiene ASIGNADAS a si
    # mismo. No incluye gateways ni next-hops, que son IPs de
    # otros equipos.

    ips = []

    if device.get("ipv4"):
        ips.append(device["ipv4"])

    for interface in device.get("interfaces") or []:
        if interface.get("ipv4"):
            ips.append(interface["ipv4"])

    return ips


def check_gateway_is_self(device):

    own = device_own_ips(device)

    warnings = []

    for field_name in ("management_gateway_ipv4", "default_route_ipv4"):

        value = device.get(field_name)

        if value and value in own:
            warnings.append(
                f"{field_name} = {value} es una IP del propio dispositivo. "
                "Deberia ser la IP del router."
            )

    return warnings


def check_duplicate_ips(device):

    own = device_own_ips(device)

    warnings = []
    seen = set()

    for ip in own:

        if ip in seen:
            warnings.append(
                f"la IP {ip} esta asignada mas de una vez en este dispositivo"
            )

        seen.add(ip)

    return warnings

def check_subinterface_encapsulation(device):
    warnings = []

    for interface in device.get("interfaces") or []:

        if interface.get("role") != "subinterface":
            continue

        encapsulation = interface.get("encapsulation")

        if encapsulation is None:
            continue

        _, _, suffix = interface["name"].partition(".")

        if suffix and int(suffix) != encapsulation:
            warnings.append(
                f"{interface['name']} tiene encapsulation dot1Q {encapsulation}. "
                f"Por convencion deberia ser {suffix}."
            )

    return warnings

def check_svi_vlan_exists(device):

    vlan_ids = {vlan["id"] for vlan in device.get("vlans") or []}

    warnings = []

    for interface in device.get("interfaces") or []:

        if interface.get("role") != "svi":
            continue

        # el nombre puede ser vlan99, Vlan99 o "vlan 99"
        match = re.search(r"(\d+)$", interface["name"])

        if match is None:
            continue

        vlan_id = int(match.group(1))

        if vlan_id not in vlan_ids:
            warnings.append(
                f"{interface['name']} necesita la VLAN {vlan_id}, "
                "que no esta definida. La SVI va a quedar up/down."
            )

    return warnings

LINT_RULES = [
    check_gateway_is_self,
    check_duplicate_ips,
    check_subinterface_encapsulation,
    check_svi_vlan_exists
]


# ============================================================
# RUN RULES
# ============================================================
#
# Pura: device -> lista de advertencias. Sin prints.
# ============================================================

def run_rules(device):

    warnings = []

    for rule in LINT_RULES:
        warnings.extend(rule(device))

    return warnings


# ============================================================
# LINT DEVICE
# ============================================================
#
# Solo imprime. No bloquea, no pregunta y no modifica el
# device: el usuario puede tener motivos para ignorar una
# advertencia.
# ============================================================

def lint_device(device):

    warnings = run_rules(device)

    if not warnings:
        return

    print()
    print("-" * 60)
    print("WARNINGS (revisar antes de aplicar)")
    print("-" * 60)

    for warning in warnings:
        print(f"  ! {warning}")

    print("-" * 60)


# ============================================================
# MODE COMMANDS
# ============================================================
#
# Estos son los comandos que se usan para entrar a cada
# contexto de configuracion. Los que terminan en espacio
# esperan un "arg" que se concatena (interface, vlan).
#
# ============================================================

MODE_COMMANDS = {
    "privileged_exec": {
        "enter": "enable",
        "parent": None
    },
    "global_config": {
        "enter": "configure terminal",
        "parent": "privileged_exec"
    },
    "line_console": {
        "enter": "line console 0",
        "parent": "global_config"
    },
    "line_vty": {
        "enter": "line vty 0 15",
        "parent": "global_config"
    },
    "interface": {
        "enter": "interface ",
        "parent": "global_config"
    },
    "interface_range": {
        "enter": "interface range ",
        "parent": "global_config"
    },
    "vlan": {
        "enter": "vlan ",
        "parent": "global_config"
    },
}

CONFIG_FILE_ROOT = "global_config"


# ============================================================
# PLAN TO TEXT
# ============================================================

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
            lines.append(f'{" " * ((i + 1) * INDENT)}exit')

        # entrar a los modos que faltan
        for i in range(common, len(target_keys)):
            mode, arg = target_keys[i]
            enter = MODE_COMMANDS[mode]["enter"]

            if arg:
                enter = f"{enter}{arg}"

            lines.append(f'{" " * (i * INDENT)}{enter}')

        indent = " " * (len(target_keys) * INDENT)

        for command in block["commands"]:
            lines.append(f"{indent}{command}")

        current_path = target_keys

    lines.append(f'{" " * (2 * INDENT)}end')
    lines.append(f'{" " * INDENT}write memory')

    return "\n".join(lines)

# ============================================================
# PRINT PLAN
# ============================================================

def get_path(mode):

    path = []
    current = mode

    while current is not None:
        path.append(current)
        current = MODE_COMMANDS[current]["parent"]

    return list(reversed(path))


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
    print(plan_to_text(plan))
    print("-" * 60)
    print()

def print_pc_plan(device):

    print()
    print("-" * 60)
    print("PC — Desktop > IP Configuration")
    print("-" * 60)

    for field_name in SECTION_FIELDS["basic"]["pc"]:

        value = device.get(field_name)

        if value is None:
            continue

        field = resolve_field(field_name, device["type"])

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
                    print(f"  - {vlan_label(vlan)}")

            continue

        if field == "interfaces":

            if not value:
                print("interfaces: none")
            else:
                print("interfaces:")
                for interface in value:
                    role = INTERFACE_ROLES[interface["role"]]["label"]
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
        # LINT DEVICE
        # ----------------------------------------------------

        lint_device(device)

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

    sections = DEVICE_SECTIONS[
        device["type"]
    ]

    print(
        f"Device type: {device['type']}"
    )

    for section in sections:

        print()

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
    # LINT DEVICE
    # ----------------------------------------------------

    lint_device(device)

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
    print(build_config_file(device))
    print("-" * 60)


# ============================================================
# MAIN
# ============================================================

def main():

    # test_plan()
    show_main_menu()


if __name__ == "__main__":
    main()
