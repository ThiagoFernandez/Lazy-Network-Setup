import auxiliar

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

INTERFACE_SIMPLE = r"[A-Za-z]+[0-9]+(?:/[0-9]+)*(?:\.[0-9]+)?"
INTERFACE_RANGE = r"[A-Za-z]+[0-9]+(?:/[0-9]+)*-[0-9]+"

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
# CONFIG FILE
# ============================================================

NOT_IN_CONFIG_FILE = {"crypto_key"} # opt
