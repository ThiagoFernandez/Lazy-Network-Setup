import re

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
