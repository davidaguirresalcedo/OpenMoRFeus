# Changelog

All notable changes to OpenMoRFeus are documented here.

## 0.3.1 — 2026-08-02

### Added

* MIT license.
* GitHub Actions continuous-integration workflow for Python 3.10–3.13.
* Automated syntax checking and execution of the complete unit-test suite.

### Changed

* Package metadata now declares the project license.
* README now displays test-status and license badges.

## 0.3.0 — 2026-08-02

### Added

* Safe frequency-sweep engine with validated start, stop, step, and dwell parameters.
* Responsive PyQt6 Sweep Generator dialog.
* Live sweep progress and verified-frequency reporting.
* Pause, resume, and controlled stop operations.
* Automatic restoration of the initial frequency after completion, stop, or error.
* Unit tests for sweep planning, execution, restoration, GUI imports, and read-back handling.

### Changed

* Frequency verification accepts the observed moRFeus quantization of ±1 Hz.
* Sweep progress reports the frequency actually confirmed by the device.

### Hardware validation

* Sweep completion, pause, resume, stop, and frequency restoration were tested with a physical moRFeus.
* The device returned to 1350 MHz after the validation sweeps.

## 0.2.0 — 2026-08-02

### Added

- Responsive PyQt6 graphical interface.
- Background hardware operations using the Qt thread pool.
- Graphical control of frequency, operating mode, mixer current,
  Bias Tee, and LCD timeout.
- Automatic state synchronization after opening the GUI.
- Apply-and-verify workflow using the hardware-validated driver.
- Optional `gui` installation dependency.
- `openmorfeus-gui` executable entry point.
- GUI controller unit tests.

### Hardware validation

- Complete state successfully read from a physical moRFeus.
- LCD timeout successfully changed, verified, refreshed, and restored.
- GUI remained responsive during HID transactions.

### Safety

- Historical selectors `0x00` and `0x86` remain unavailable.

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
