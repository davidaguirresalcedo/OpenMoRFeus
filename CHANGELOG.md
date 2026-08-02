# Changelog

All notable changes to OpenMoRFeus are documented here.

## 0.1.0 — 2026-08-02

Initial hardware-validated release.

### Added

- Binary HID report encoder and decoder.
- Read-only access to documented moRFeus settings.
- Validated and read-back-verified SET operations.
- SET acknowledgement handling using opcode `0x77`.
- Initial HID queue draining after device open.
- Response correlation by opcode and function selector.
- Configurable transaction timeout and polling interval.
- Command-line interface for reading and changing settings.
- Editable Python package installation through `pyproject.toml`.
- `udev` rule for non-root access to USB HID device `10c4:eac9`.
- Automated unit tests for protocol, driver, transactions, and CLI.

### Hardware validation

Validated against a physical Outernet moRFeus with:

- Frequency: 1350 MHz
- Mode: Generator
- Mixer current: 0
- Bias Tee: Off
- LCD timeout: Always on

The implementation was tested with deliberately stale GET and
SET acknowledgement reports to verify queue draining and response
correlation.

### Safety

Historical selectors `0x00` and `0x86` are intentionally not
exposed through the public driver or CLI.
