# OpenMoRFeus

[![Tests](https://github.com/davidaguirresalcedo/OpenMoRFeus/actions/workflows/tests.yml/badge.svg)](https://github.com/davidaguirresalcedo/OpenMoRFeus/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
Open implementation and technical documentation for controlling the
Outernet moRFeus RF generator and frequency mixer through USB HID.

## Installation

Create or activate a Python virtual environment and install the project:

```console
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

The installed command is:

```console
.venv/bin/openmorfeus --help
```

### USB access without root privileges

OpenMoRFeus includes a `udev` rule for the Outernet moRFeus USB HID
identifiers `10c4:eac9`.

Install it with:

```console
sudo install -m 0644       packaging/udev/99-openmorfeus.rules       /etc/udev/rules.d/99-openmorfeus.rules

sudo udevadm control --reload-rules
sudo udevadm trigger
```

Disconnect and reconnect the moRFeus after installing the rule.

The device can then be accessed without running the Python application
as root.

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
- [x] Modern Python driver.
- [x] Command-line interface.
- [x] Responsive PyQt6 graphical interface.
- [x] Safe frequency sweep generator with automatic restoration.
- [x] Automated unit tests and GitHub Actions CI.
- [ ] Legacy morfeus_tool compatibility layer.
- [ ] Automated hardware-in-the-loop tests with a physical moRFeus.
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

OpenMoRFeus is released under the MIT License. See
[`LICENSE`](LICENSE) for the complete terms.

## Command-line interface

OpenMoRFeus includes a command-line interface for the documented
moRFeus controls.

```console
openmorfeus state
openmorfeus get frequency
openmorfeus get mode

openmorfeus set frequency 1350MHz
openmorfeus set mode generator
openmorfeus set mixer-current 0
openmorfeus set bias-tee off
openmorfeus set lcd-timeout always-on
```

Bare frequency values are interpreted as MHz. Explicit `Hz`,
`kHz`, `MHz`, and `GHz` units are supported.

The historical selectors `0x00` and `0x86` are intentionally not
exposed.


## Graphical interface

Install the optional PyQt6 dependency and launch the GUI:

```console
python -m pip install -e '.[gui]'
openmorfeus-gui
```

Hardware transactions run outside the graphical event loop.
The GUI exposes only the documented controls. Historical
selectors `0x00` and `0x86` remain unavailable.


### Sweep generator

The graphical interface includes a responsive frequency-sweep
dialog with:

- validated start, stop, and step frequencies;
- configurable dwell time;
- live progress and current-frequency display;
- pause, resume, and stop control;
- automatic restoration of the initial frequency.

The sweep runs outside the Qt event thread. Closing the dialog
during execution requests a controlled stop before the window
is closed.
