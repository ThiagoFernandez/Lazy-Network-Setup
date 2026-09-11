# Lazy Network Setup

A program that lets you automate your network setup in a lazy way: it asks you questions and gives you back the Cisco IOS commands, ready to paste into a terminal or to save as a configuration file.

> Built while studying CCNA. For anyone tired of typing the same basic configuration twenty times in Packet Tracer.

## Usage

```bash
pip install -r requirements.txt
python main.py
```

The main menu offers two ways to build a configuration:

- **Guided Setup** — walks you through every section of the device, in order.
- **Categories Setup** — pick a device, then pick the sections you want, in any order.

Supported devices: `pc`, `switch`, `router`.

When a section is done, the program shows the resulting plan and offers three outputs:

1. **Screen** — the IOS commands with their mode context and indentation.
2. **Clipboard** — the same text, ready to paste into Packet Tracer or a terminal.
3. **Config file** — `configs/<hostname>.txt`, in configuration-file style, loadable through *Config → Load* in Packet Tracer.

A PC has no IOS commands: the program prints the values to type into *Desktop → IP Configuration*.

### Example

A switch configured with the `basic`, `security` and `interfaces` sections:

```text
enable
 configure terminal
  hostname sw-test
  service password-encryption
  ip default-gateway 192.168.0.1
  banner motd #only authorized#
  ip domain-lookup
  enable secret hola123
  username thiagouser privilege 15 secret thiagopass
  ip domain-name casa.com
  crypto key generate rsa
  1024
  ip ssh version 2
  line console 0
   password hola231
   login
   exit
  line vty 0 15
   password hola312
   login
   login local
   transport input ssh
   exit
  vlan 20
   name FINANZAS
   exit
  vlan 99
   name GESTION
   exit
  interface vlan99
   ip address 192.168.0.10 255.255.255.0
   no shutdown
   exit
  interface range fa0/1-12
   description PCs finanzas
   switchport mode access
   switchport access vlan 20
   no shutdown
   exit
  interface g0/1
   switchport mode trunk
   switchport trunk allowed vlan 20,99
  end
 write memory
```

Note the `1024` on its own line: `crypto key generate rsa` asks for the modulus interactively, and the answer travels as the next line of the pasted block.

## How does it work?

The program is divided into four layers, each with a different responsibility.

### 1. Intention

This layer collects and validates the user's input and builds the device dictionary. `setup_section` handles the flat scalar fields; `vlans_setup` and `interfaces_loop` handle the collections. All three validate values and honour `CANCEL` and `SKIP`.

The resulting device dictionary contains no Cisco syntax. Its keys describe what the user wants, such as `dns_lookup: False`, rather than how Cisco IOS writes that configuration. This keeps the intention independent from the command language, so supporting another vendor would mean adding another rendering strategy instead of rewriting the questionnaire and its data model.

```python
{
    "type": "switch",
    "hostname": "SW-TEST",
    "dns_lookup": False,

    "vlans": [
        {"id": 20, "name": "FINANZAS"},
        {"id": 99, "name": "GESTION"}
    ],

    "interfaces": [
        {"name": "vlan99", "role": "svi",
         "ipv4": "192.168.0.10", "mask_ipv4": "255.255.255.0",
         "shutdown": False},
        {"name": "fa0/1-12", "role": "access",
         "description": "PCs finanzas", "access_vlan": 20,
         "shutdown": False}
    ]
}
```

The dictionary represents the desired state, not the commands needed to achieve it.

The structure is deliberately mixed. Scalar fields sit flat at the root because there is exactly one of each — a switch has one console password. `vlans` and `interfaces` are lists because there are many, and because **order matters**: VLANs must be created before ports are assigned to them, otherwise IOS auto-creates them without a name.

### 2. Render

This layer converts individual values into IOS commands. Different renderers handle different command types, while `render_field` chooses the appropriate strategy.

This is the only layer that knows IOS syntax. `{"hostname": "SW-TEST"}` becomes `hostname SW-TEST`; `{"dns_lookup": False}` becomes `no ip domain-lookup`. The renderer does not need to know how the questionnaire works, where the value came from, or whether the final output will go to the screen, clipboard, or a file.

Most renderers map one value to one command. Two do not:

- `multiple` maps one value to several commands. `access_vlan: 20` produces both `switchport mode access` and `switchport access vlan 20`, because those two are inseparable in practice — a port assigned to a VLAN without being set to access mode is a misconfiguration, so the questionnaire never lets them come apart.
- `template` maps **several values to one command**. This is what `ip address <address> <mask>` needs. See *Virtual fields* below.

### 3. Plan

`build_plan` takes the generated commands and groups them into blocks. Each block records which IOS mode the commands belong to, and — for parameterised modes — which instance:

```python
[
    {"mode": "global_config", "commands": ["hostname R1"]},
    {"mode": "line_console",  "commands": ["password cisco", "login"]},
    {"mode": "vlan", "arg": "20", "commands": ["name FINANZAS"]},
    {"mode": "interface", "arg": "g0/1",
     "commands": ["switchport mode trunk",
                  "switchport trunk allowed vlan 20,99"]}
]
```

The plan is not a flat list of strings because the mode of each command matters. A flat list such as:

```text
hostname R1
password cisco
login
```

would lose the information that `hostname` belongs to `global_config`, while `password` and `login` belong to `line_console`.

Nor is the plan a dictionary keyed by mode. It was, until interfaces arrived: a switch has many interfaces and all of them are in mode `interface`, so as a dictionary the second one would overwrite the first. A list allows the mode to repeat, and `arg` distinguishes the instances.

A block whose `commands` list is empty is still emitted when the mode entry is itself meaningful: `vlan 30` with no name creates the VLAN, so the block is kept even though it carries no commands.

### 4. Serialization

This layer converts the plan into text. There are two formats:

```text
                         PLAN
                        /    \
                       /      \
              plan_to_text   build_config_file
                    ↓              ↓
               IOS terminal    config file
```

`plan_to_text` generates commands for a terminal, including mode transitions, `exit` commands and indentation. The mode hierarchy is stored as data in `MODE_COMMANDS` (each mode has its `enter` command and its `parent`); `get_path` follows the `parent` relationships to work out how to move between modes. Adding a new mode does not require another branch in the serializer — only its entry command and its parent.

Navigation compares the **path** of the previous block against the path of the next one: the shared prefix says how many `exit` commands to emit and which modes to enter. The identity of a node in that path is the pair `(mode, arg)`, not the mode alone — without the `arg`, two consecutive `interface` blocks would share a full prefix and the second interface's commands would end up inside the first.

`build_config_file` generates a configuration-file dialect instead: it starts with `!`, writes global configuration first, does not include `enable` or `configure terminal`, separates blocks with `!` and ends with `end`. The mode entry commands come from the same `MODE_COMMANDS`; there is no second table.

```text
!
hostname SW-1
enable secret c
!
line console 0
 password a
 login
!
vlan 99
 name GESTION
!
interface vlan99
 ip address 192.168.0.10 255.255.255.0
 no shutdown
!
end
```

The single space of indentation is not cosmetic here: it is how the IOS parser recognises that a command belongs to the preceding block. (In `plan_to_text` the indentation *is* cosmetic — a terminal ignores leading whitespace.)

Some commands are intentionally excluded from the file: `crypto key generate rsa` creates device state rather than describing configuration, so it renders for the terminal but is left out of the config file (the program says so when it saves).

Neither serializer prints directly. Both return the resulting text.

### Overall flow

```text
User
 ↓
INTENTION
 ↓
Device dictionary  (scalars + vlans[] + interfaces[])
 ↓
RENDER
 ↓
IOS commands
 ↓
PLAN
 ↓
Blocks: mode + arg + commands
 ↓
LINT (warnings only — reads the device, changes nothing)
 ↓
SERIALIZATION
 ↓
Terminal text ──→ screen, clipboard
Config file   ──→ configs/<hostname>.txt
                  (future transports: serial console, SSH — same text, different destination)
```

Each layer adds information without mixing responsibilities: Intention defines *what* the user wants, Render defines *which commands* represent it, Plan preserves *where* those commands belong, and Serialization defines *how* the final result is written. The three output choices are therefore not three separate configuration paths: they are three consumers of the same plan.

`build_plan` performs no I/O — no `print`, no `input`. That is what makes it possible to test the entire rendering pipeline against a hand-written device dictionary, without answering a single question.

## Adding a field

Every field is defined once, in `FIELD_DEFINITIONS`. A field has two halves:

- what the questionnaire needs: `question`, `validator`, `label`;
- what the render needs, which may depend on the device: `mode`, `render`, `descriptor`.

`SECTION_FIELDS` determines which flat fields belong to each section and device type:

```text
SECTION_FIELDS
├── basic
│   ├── pc
│   ├── switch
│   └── router
├── security
│   ├── pc        (empty)
│   ├── switch
│   └── router
└── interfaces
    ├── pc        (empty)
    ├── switch    (empty — handled by INTERFACE_ROLES, see below)
    └── router    (empty — idem)
```

The `interfaces` entries are empty on purpose. Interfaces stopped being flat fields when they became a list; the section still exists in `DEVICE_SECTIONS` so that it appears in the menu, but `interfaces_setup` calls the sub-loops instead of `setup_section`.

### 1. A field that behaves the same on every device

A field such as `banner` does not need a different target per device. Its definition holds the questionnaire information and the rendering information directly:

```python
"banner": {
    "question": "Write the banner",
    "validator": auxiliar.validate_optional_string,

    "mode": "global_config",
    "render": "delimited",
    "descriptor": "banner motd"
}
```

The field name is then added to the device lists it applies to, e.g. `SECTION_FIELDS["basic"]["switch"]`. The definition is not duplicated just because more than one device uses it.

### 2. A field that is written differently depending on the device

Some configuration concepts look like one field but are actually different concepts. The default gateway is a good example:

- a **switch** configures its management gateway with `ip default-gateway <address>`;
- a **PC** receives the same kind of management information through *Desktop → IP Configuration*;
- a **router** is different: its equivalent is a routing decision, `ip route 0.0.0.0 0.0.0.0 <address>`.

So there are two fields, not one: `management_gateway_ipv4` (host management information, used by PCs and switches) and `default_route_ipv4` (routing information, used by routers).

The device-dependent part of a field lives under `targets`, indexed by device type:

```python
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
}
```

The PC target is explicit. `"mode": None, "render": None` means the field is a valid part of the PC's intention but produces no IOS command; the value is still there for the PC output to display.

That is different from the target being absent. If a device appears in `SECTION_FIELDS` but has no corresponding target in the field definition, the program raises an error instead of silently doing nothing. This is deliberate: an absent target is a configuration-definition error, not a valid "nothing to do" case. Silently skipping it would hide a mismatch between the section catalog and the field definition.

The resolution happens in `resolve_field(field_name, device_type)`: it takes the shared field definition, selects the target for the requested device, and returns the same field shape that the rendering code expects.

```text
FIELD_DEFINITIONS
      ↓
resolve_field()
      ↓
correct target for this device
      ↓
same field dictionary shape
      ↓
render_field()
      ↓
renderer
```

### 3. What does NOT change

The renderers do not change. `resolve_field` selects the device-specific target before rendering, so `render_field` receives the same kind of field dictionary it always received. Device-specific behavior is handled at field resolution rather than duplicated throughout the renderers — adding a new device-specific representation does not require another renderer just because the target device changed.

## Interfaces and VLANs

Interfaces are not flat fields: a device has an arbitrary number of them, each with its own set of relevant settings. A switch access port needs a VLAN; a trunk needs an allowed list and a native VLAN; a router subinterface needs an encapsulation and an address. Those are four different questionnaires.

The discriminator is the **role**, declared in `INTERFACE_ROLES`:

```python
"svi": {
    "label": "SVI (management)",
    "device_types": ["switch"],
    "name_pattern": _SVI,
    "name_hint": "vlan99",
    "ask_fields": ["description", "ipv4", "mask_ipv4", "shutdown"],
    "render_fields": ["description", "ip_address", "shutdown"]
}
```

Current roles: `access`, `trunk` and `svi` for switches; `subinterface` for routers.

`device_types` filters the role menu, so a router is never offered `access` and a switch is never offered `subinterface`. An empty list works as an off switch: a role can be fully defined and still stay out of the menu while its renderer does not exist yet.

### Asking is not rendering

`ask_fields` and `render_fields` are two different lists, because **a question does not map one-to-one to a command**. `ip address 172.17.10.1 255.255.255.0` is a single command that requires two answers. So `ask_fields` contains `ipv4` and `mask_ipv4` — what the user is asked — and `render_fields` contains `ip_address` — what is emitted.

For `access` and `trunk` the two lists happen to be identical, because there the correspondence *is* one-to-one. The separation exists for the cases where it is not.

The order of `render_fields` is functional, not cosmetic. In `subinterface`, `encapsulation` comes before `ip_address` because that is the order IOS expects.

### Virtual fields

A virtual field is one the user is never asked about. It declares which real fields it consumes:

```python
"ip_address": {
    "requires": ["ipv4", "mask_ipv4"],

    "mode": "interface",
    "render": "template",
    "commands": ["ip address {ipv4} {mask_ipv4}"]
}
```

`build_interface_commands` detects the `requires` key, collects those values from the interface into a dictionary, and hands the whole dictionary to `render_template` instead of a single value. If any required value is missing, the command is skipped rather than emitted half-built — an SVI with an address but no mask produces no `ip address` line at all.

The same mechanism generalises: `ipv6 address {ipv6}/{prefix}` would be another virtual field, with no new renderer and no change to the engine.

### Names are validated per role

Each role declares which shape its interface name may take, as a regex:

| Role | Accepts | Example |
|---|---|---|
| `access`, `trunk` | physical port or range | `g0/1`, `fa0/1-12` |
| `svi` | VLAN interface | `vlan99` |
| `subinterface` | port with subinterface suffix | `g0/0/1.10` |

This exists because the two halves are independently valid but jointly wrong. Choosing the `svi` role and typing `f0/1` produces `ip address` on a layer-2 switchport, which IOS rejects with `% Invalid input detected` — a 2960 access port has no `ip address` command at all, because the switch's IP lives on a virtual VLAN interface, not on a physical port.

For the same reason the role is asked **before** the name: the role is what determines which names are valid.

Ranges are detected from the name. A hyphen selects the `interface_range` mode, so `fa0/1-12` emits `interface range fa0/1-12` and configures twelve ports in one block.

## Consistency checks

Every validator rejects a badly formed value, so the engine never sees one. That is not enough: individually valid answers can still combine into a configuration that IOS accepts and that does not work.

The clearest example is a subinterface named `g0/0/1.10` carrying `encapsulation dot1Q 30`. Both answers are valid. The result is syntactically correct, every interface reports `up/up`, and inter-VLAN routing silently does not work — a host in VLAN 10 has its frames received by the subinterface that lives in another subnet, so its gateway never answers. Nothing in `show ip interface brief` points at the cause.

`lint_device` runs over the finished device, after the plan is built and before it is printed. It reports warnings and does nothing else: it never blocks, never asks for confirmation and never modifies the device. The user may have a reason to ignore a warning — a VLAN that will be created by hand, for instance — and the program is not in a position to overrule that.

Each rule is a function that takes the device and returns a list of strings; `run_rules` concatenates them and performs no I/O, so the whole thing is testable against a hand-written device dictionary. Adding a rule means writing a function and appending it to `LINT_RULES`; the engine does not change.

Current rules:

| Rule | What it catches |
|---|---|
| `check_gateway_is_self` | the default gateway or default route points at one of the device's own addresses |
| `check_duplicate_ips` | the same address assigned more than once on this device |
| `check_subinterface_encapsulation` | the subinterface suffix does not match its `encapsulation dot1Q` |
| `check_svi_vlan_exists` | an SVI whose VLAN is not in the VLAN database — the interface would come up `up/down` |

Two notes on the last two rules.

The subinterface suffix is **arbitrary as far as IOS is concerned**: `g0/0/1.847` with `encapsulation dot1Q 10` works perfectly. What determines which VLAN a subinterface serves is the encapsulation alone. Matching the suffix to the VLAN is a convention, not a requirement — which is exactly why it is reported as a warning rather than rejected at entry.

An SVI also needs at least one **active port** in its VLAN, not just the VLAN to exist. A VLAN present in the database with no access port up and no trunk carrying it still leaves the SVI `up/down`. That condition is not checked yet.

## Status

### What works today

- **`basic` and `security`** for `switch` and `router`: hostname, passwords (console, VTY, enable secret), banner, password encryption, DNS lookup, default gateway / default route, domain name, RSA keys, users, SSH version, `login local`, `transport input`, minimum password length.
- **`basic`** for `pc`: IPv4 and IPv6 addressing, mask, prefix, link-local, gateway, DNS — printed as a field list for *Desktop → IP Configuration*.
- **`interfaces`** for `switch`: VLAN database (create, edit, remove; ID and optional name), access ports, trunk ports, SVIs. Port ranges supported.
- **`interfaces`** for `router`: 802.1Q subinterfaces — the full router-on-a-stick.
- **Outputs**: screen, clipboard, configuration file.
- **Consistency checks**: the finished device is linted before the plan is printed. See *Consistency checks* below.

The switch is now reachable over the network: an SVI plus a default gateway is enough to reach it over SSH.

### What is missing

- **Physical interfaces on routers.** The only router role is `subinterface`, so there is no way to configure `g0/0/0` with an address — no WAN link, no point-to-point, and no `no shutdown` for the physical parent of a subinterface. A subinterface does not come up while its parent is administratively down. This is the largest remaining gap, and it is a data-only change: a role with the same shape as `svi`.
- **Port security**, spanning-tree and EtherChannel. Port security fits the existing `access` role as four extra fields; STP mixes global and per-interface commands; EtherChannel introduces a new object (the port-channel is a logical interface with member interfaces) and would probably need its own list in the device.
- **Multi-device.** One device per run. A six-switch topology means six runs.
- **Persistence.** The device is lost on exit and the generated `.txt` cannot be read back in.
- **More consistency checks.** Four rules exist; the catalog is not complete. Still unchecked: a port assigned to a VLAN that was never created, a trunk allowing VLANs that do not exist, overlapping port ranges, an address outside its own mask, and IPv4/IPv6 fields that accept either family.
- **Real transports.** Today the program generates configuration; it does not apply it to a device.

The transport roadmap is:

```text
Serial console (pyserial)
        ↓
Configure the device, including SSH
        ↓
SSH transport (netmiko)
```

The order matters. A factory switch has no management IP, no RSA keys and no user credentials, so SSH is impossible on first contact. The serial console is the bootstrap: it lets the program configure the device — including the SSH access that the program's own SSH transport will use afterwards.

### Roadmap

- **M1** — questionnaire → intention → render → plan → screen. ✅ Verified on a clean Packet Tracer switch.
- **M2** — clipboard and configuration-file outputs, sharing the same plan. ✅
- **M3a** — catalog: VLANs, access and trunk ports, SVI, router subinterfaces. ✅
- **M3b** — remaining catalog: physical router interfaces, port security, STP, EtherChannel.
- **M3c** — consistency checks over the finished device, reported as warnings rather than blocking errors. ◐ Engine done, four rules in place; catalog incomplete.
- **M4** — serial console transport (`pyserial`), against a real switch.
- **M5** — SSH transport (`netmiko`), once M4 has made SSH possible.
- **M6** — compliance check: read `show running-config` and compare it against the intention.

## Verification

Reported according to what has actually been tested.

- **Switch, `basic` + `security` — 2026-09-03.** Generated by the program and pasted into Cisco Packet Tracer. Every command accepted, SSH enabled, `write memory` completed.
- **PC — 2026-09-03.** Configured manually through *Desktop → IP Configuration* using the values printed by the program.
- **Configuration file — verified.** A generated `configs/<hostname>.txt` was loaded through *Config → Load* in Packet Tracer and applied without errors. Worth noting: `interface range` is a CLI convenience command and does not appear in a real `show running-config`, where each port is listed separately. Packet Tracer's Load parser accepts it; this has not been verified against real hardware.
- **Router, `subinterface` role — generated and reviewed, not yet pasted.** The rendered output places `encapsulation dot1Q` before `ip address` on each subinterface, which is the ordering IOS requires.
- **Router, `basic` — 2026-08-24.** Generated and verified in Packet Tracer. This predates the `targets` refactor, so it does not verify the current field-resolution code; in particular `default_route_ipv4` should be considered unverified until it is generated with the current code and pasted again.
- **Real hardware.** Not yet tested. The first meaningful hardware verification will be the serial-console transport.

### A note on `transport input`

The protocol list offered by the questionnaire includes legacy IOS protocols (`rlogin`, `lat`, `mop`, `nasi`, `pad`, `udptn`, `v120`, `acercon`) that **Packet Tracer does not implement**. Selecting one produces `% Invalid input detected` on the second protocol of the line. Packet Tracer supports `ssh`, `telnet`, `all` and `none`. Additionally `all` and `none` are mutually exclusive with the named protocols and cannot be combined with them.
