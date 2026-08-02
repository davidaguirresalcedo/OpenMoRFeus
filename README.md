# OpenMoRFeus

Open implementation and technical documentation for controlling the
Outernet moRFeus RF generator and frequency mixer through USB HID.

## Project objectives

- Document the moRFeus USB HID protocol.
- Provide a modern Python API.
- Provide a command-line interface.
- Restore compatibility with legacy software.
- Integrate moRFeus into automated RF test benches.

## Current status

- [x] USB device enumeration confirmed.
- [x] HID read communication confirmed.
- [x] HID write communication confirmed.
- [x] Frequency control confirmed.
- [x] GET frame format documented.
- [x] SET frame format documented.
- [x] Function selectors 0x81 through 0x85 validated.
- [x] Textual error response observed.
- [ ] Modern Python driver.
- [ ] Command-line interface.
- [ ] Legacy morfeus_tool compatibility layer.
- [ ] Automated tests with physical hardware.
- [ ] RF laboratory integration.

## Device identity

| Property | Value |
|---|---|
| Manufacturer | Outernet |
| Product | moRFeus |
| USB Vendor ID | 0x10C4 |
| USB Product ID | 0xEAC9 |
| USB class | HID |

## Repository layout

OpenMoRFeus/
- README.md
- docs/
  - HID_PROTOCOL_SPEC.md
  - ENGINEERING_LOG.md
- experiments/
- src/
  - openmorfeus/
    - __init__.py
- tests/

## Safety note

Selector 0x86, historically named Firmware Mode, has not been tested
with a SET operation. It may cause a reset or place the device in a
firmware-update state. It must not be exercised until a recovery
procedure is established.

## License

To be selected before public release.
