# OpenMoRFeus Engineering Log

## EN-001 - USB enumeration

Date: 2026-08-02
Status: Confirmed

Observed device identity:

    Vendor ID:    0x10C4
    Product ID:   0xEAC9
    Manufacturer: Outernet
    Product:      moRFeus
    USB class:    HID

The device was accessible through Linux hidraw and Python hidapi.

## EN-002 - Bidirectional HID communication

Date: 2026-08-02
Status: Confirmed

The device accepted HID writes and returned HID responses.

A frequency change from 1300 MHz to 1350 MHz was performed through
Python and confirmed on the physical device display.

## EN-003 - Logical report structure

Date: 2026-08-02
Status: Confirmed

The logical HID report contains 16 bytes:

    1-byte opcode
    1-byte function selector
    8-byte unsigned big-endian value
    6-byte trailer

A host write through hidapi contains an additional leading Report ID
equal to 0x00, producing a 17-byte Python write buffer.

## EN-004 - GET Frequency capture

Date: 2026-08-02
Status: Confirmed

Host write buffer:

    00 72 81 00 00 00 00 00 00 00 00 00 00 00 00 00 00

Device response:

    72 81 00 00 00 00 50 77 5D 80 00 00 00 00 00 00

Decoded value:

    1,350,000,000 Hz
    1350 MHz

## EN-005 - Function-selector survey

Date: 2026-08-02
Status: Confirmed for GET selectors 0x81 through 0x85

Observed state:

| Selector | Function | Value | Interpretation |
|---|---|---:|---|
| 0x81 | Frequency | 1350000000 | 1350 MHz |
| 0x82 | Mixer or Generator | 1 | Generator |
| 0x83 | Mixer current | 0 | Current setting 0 |
| 0x84 | Bias Tee | 0 | Off |
| 0x85 | LCD timeout | 0 | Always on |

## EN-006 - Textual error response

Date: 2026-08-02
Status: Confirmed

GET selector 0x86 returned:

    Invalid param.

Raw response:

    49 6E 76 61 6C 69 64 20 70 61 72 61 6D 2E 00 00

This response must not be interpreted as a normal binary uint64 report.

## EN-007 - Historical selector 0x86

Date: 2026-08-02
Status: Historical evidence found; SET behavior not validated

Repository-history analysis found that selector 0x86 appeared on
2018-04-25 under the name:

    funcfirmwareMode = 134

The historical source also contained a commented SET command template:

    00 77 86 00 00 00 00 00 00 00 00 00 00 00 00 00 00

No successful hardware test, response parser, or active GUI function
was found for this command.

Decision:

    Do not transmit SET 0x86 until a recovery procedure exists.

## EN-008 - Initial protocol baseline

Date: 2026-08-02
Status: Completed

Document OMRF-SPEC-001 Revision 0.1 was created from source-code
analysis, Git-history investigation, and physical-device experiments.
