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
3. **Config file** — `configs/<hostname>.txt`, in configuration-file style.

A PC has no IOS commands: the program prints the values to type into *Desktop → IP Configuration*.

### Example

A switch configured with the `basic` and `security` sections produces this plan (real output, pasted into Packet Tracer without a single error):

```text
enable
 configure terminal
  hostname sw-test
  service password-encryption
  ip default-gateway 192.168.0.2
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
  end
 write memory
```

Note the `1024` on its own line: `crypto key generate rsa` asks for the modulus interactively, and the answer travels as the next line of the pasted block.

## How does it work?

The program is divided into four layers, each with a different responsibility.

### 1. Intention

This layer collects and validates the user's input and builds the device dictionary. `setup_section` is the main function: it processes the fields, validates values, and handles `CANCEL` and `SKIP`.

The resulting device dictionary contains no Cisco syntax. Its keys describe what the user wants, such as `dns_lookup: False`, rather than how Cisco IOS writes that configuration. This keeps the intention independent from the command language, so supporting another vendor would mean adding another rendering strategy instead of rewriting the questionnaire and its data model.

```python
{
    "type": "switch",
    "hostname": "SW-TEST",
    "dns_lookup": False
}
```

The dictionary represents the desired state, not the commands needed to achieve it.

### 2. Render

This layer converts individual values into IOS commands. Different renderers handle different command types, while `render_field` chooses the appropriate strategy.

This is the only layer that knows IOS syntax. `{"hostname": "SW-TEST"}` becomes `hostname SW-TEST`; `{"dns_lookup": False}` becomes `no ip domain-lookup`. The renderer does not need to know how the questionnaire works, where the value came from, or whether the final output will go to the screen, clipboard, or a file.

### 3. Plan

`build_plan` takes the generated commands and groups them by IOS mode.

The plan is not a list of strings because the mode of each command is important. A flat list such as:

```text
hostname R1
password cisco
login
```

would lose the information that `hostname` belongs to `global_config`, while `password` and `login` belong to `line_console`. Instead, the plan preserves that structure:

```python
{
    "global_config": ["hostname R1"],
    "line_console": ["password cisco", "login"]
}
```

This allows the program to reuse the same plan for different outputs.

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
line vty 0 15
 password b
 login
 login local
!
end
```

Some commands are intentionally excluded from the file: `crypto key generate rsa` creates device state rather than describing configuration, so it renders for the terminal but is left out of the config file (the program says so when it saves).

Neither serializer prints directly. Both return the resulting text.

### Overall flow

```text
User
 ↓
INTENTION
 ↓
Device dictionary
 ↓
RENDER
 ↓
IOS commands
 ↓
PLAN
 ↓
Commands grouped by mode
 ↓
SERIALIZATION
 ↓
Terminal text ──→ screen, clipboard
Config file   ──→ configs/<hostname>.txt
                  (future transports: serial console, SSH — same text, different destination)
```

Each layer adds information without mixing responsibilities: Intention defines *what* the user wants, Render defines *which commands* represent it, Plan preserves *where* those commands belong, and Serialization defines *how* the final result is written. The three output choices are therefore not three separate configuration paths: they are three consumers of the same plan.

## Adding a field

Every field is defined once, in `FIELD_DEFINITIONS`. A field has two halves:

- what the questionnaire needs: `question`, `validator`, `label`;
- what the render needs, which may depend on the device: `mode`, `render`, `descriptor`.

`SECTION_FIELDS` determines which fields belong to each section and device type:

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
    ├── switch    (empty)
    └── router    (empty)
```

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

## Status

### What works today

The current catalog in `SECTION_FIELDS` covers the `basic` and `security` sections for `switch` and `router` (hostname, passwords, banner, password encryption, DNS lookup, default gateway / default route, domain name, RSA keys, users, SSH version, `login local`, `transport input`) and the `basic` section for `pc` (addresses, mask, gateway, DNS). Outputs: screen, clipboard, configuration file.

### What is missing

- **The `interfaces` section** (SVIs, physical interfaces). Until it exists, a configured switch can have a default gateway but no IP address of its own, so it is **not yet reachable over the network**.
- VLANs, trunks, port-security and the rest of the CCNA 2 catalog.
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
- **M3a** — catalog: SVI and interfaces, VLANs, trunks, port-security.
- **M3b** — serial console transport (`pyserial`), against a real switch.
- **M4** — SSH transport (`netmiko`), once M3b has made SSH possible.
- **M5** — compliance check: read `show running-config` and compare it against the intention.

## Verification

Reported according to what has actually been tested.

- **Switch — 2026-09-03.** A configuration with the current `basic` + `security` sections was generated by the program and pasted into Cisco Packet Tracer. Every command was accepted, SSH was enabled, `write memory` completed.
- **PC — 2026-09-03.** Configured manually through *Desktop → IP Configuration* using the values printed by the program.
- **Router — 2026-08-24.** Generated and verified in Packet Tracer. This predates the `targets` refactor, so it does not verify the current field-resolution code; in particular `default_route_ipv4` should be considered unverified until it is generated with the current code and pasted again.
- **Real hardware.** Not yet tested. The first meaningful hardware verification will be the serial-console transport.
