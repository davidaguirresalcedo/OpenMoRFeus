# OpenMoRFeus HID Protocol Specification

Document: OMRF-SPEC-001
Revision: 0.1
Status: Experimental
Date: 2026-08-02

## 1. Scope

This document describes the USB HID protocol experimentally observed
between a Linux host and an Outernet moRFeus RF generator and mixer.

Only behavior confirmed through source-code analysis, repository
history, or physical-device testing is marked as confirmed.

## 2. USB device identity

| Field | Value |
|---|---|
| Vendor ID | 0x10C4 |
| Product ID | 0xEAC9 |
| Manufacturer | Outernet |
| Product | moRFeus |
| Interface class | USB HID |

The tested Linux system exposed the device through a hidraw interface.

## 3. Report size

The logical moRFeus HID report is 16 bytes long.

For writes through hidapi, the host supplies an additional leading
Report ID byte equal to 0x00. Therefore, the Python write buffer contains
17 bytes.

## 4. Logical report format

The 16-byte logical report has the following structure:

| Offset | Size | Field |
|---:|---:|---|
| 0 | 1 byte | Operation opcode |
| 1 | 1 byte | Function selector |
| 2 | 8 bytes | Unsigned value, big-endian |
| 10 | 6 bytes | Trailer or reserved bytes |

Report layout:

    Byte     0        1          2 through 9       10 through 15
           +--------+----------+------------------+---------------+
           | Opcode | Function | uint64 big-endian| Trailer       |
           +--------+----------+------------------+---------------+

All trailer bytes observed during validated GET operations were zero.

## 5. Operation opcodes

| Operation | Decimal | Hexadecimal | ASCII |
|---|---:|---:|---|
| GET or Read | 114 | 0x72 | r |
| SET or Write | 119 | 0x77 | w |

The interpretation of r as read and w as write is supported by the
observed protocol behavior.

## 6. Value encoding

The value field is encoded as an unsigned 64-bit integer using
big-endian byte order.

Python equivalent:

    encoded = value.to_bytes(8, byteorder="big", signed=False)
    decoded = int.from_bytes(encoded, byteorder="big", signed=False)

For frequency operations, the value is expressed in hertz.

## 7. Function selectors

| Selector | Function | Known values | Validation status |
|---|---|---|---|
| 0x81 | Frequency | Frequency in Hz | GET and SET confirmed |
| 0x82 | Mixer or Generator mode | 0: Mixer, 1: Generator | GET and SET confirmed |
| 0x83 | Mixer current | Integer from 0 through 7 | GET confirmed |
| 0x84 | Bias Tee | 0: Off, 1: On | GET confirmed |
| 0x85 | LCD timeout | 0: Always on, 1: 10 s, 2: 60 s | GET confirmed |
| 0x86 | Historical Firmware Mode | Historical SET value: 0 | GET rejected; SET not tested |
| 0x00 | Historical Register selector | Unknown | Not tested |

Selector 0x86 and selector 0x00 must not be exercised until their
behavior and recovery procedures are understood.

## 8. Confirmed GET Frequency exchange

The host requested the current frequency using the following 17-byte
hidapi write buffer:

    00 72 81 00 00 00 00 00 00 00 00 00 00 00 00 00 00

Field interpretation:

    00                         HID Report ID
    72                         GET opcode
    81                         Frequency selector
    00 00 00 00 00 00 00 00  Request value
    00 00 00 00 00 00        Trailer

The device returned this 16-byte response:

    72 81 00 00 00 00 50 77 5D 80 00 00 00 00 00 00

The value field was:

    00 00 00 00 50 77 5D 80

Decoded as an unsigned 64-bit big-endian integer:

    1,350,000,000 Hz

Therefore, the device frequency was:

    1350 MHz

## 9. Confirmed device-state readings

A sequence of GET requests produced the following results:

| Selector | Raw value | Interpretation |
|---|---:|---|
| 0x81 | 1350000000 | Frequency: 1350 MHz |
| 0x82 | 1 | Generator mode |
| 0x83 | 0 | Mixer current setting 0 |
| 0x84 | 0 | Bias Tee off |
| 0x85 | 0 | LCD always on |

All validated binary responses used opcode 0x72 and contained six zero
bytes in the trailer field.

## 10. Textual error response

A GET request using selector 0x86 returned:

    49 6E 76 61 6C 69 64 20 70 61 72 61 6D 2E 00 00

ASCII decoding produced:

    Invalid param.

This response does not follow the normal binary response format.

Software implementations must detect textual responses before decoding
bytes 2 through 9 as a 64-bit integer.

Only the exact message "Invalid param." has been experimentally
observed. Other error messages remain undocumented.


## 11. Historical selector 0x86

Repository-history analysis found that selector 0x86 first appeared on
2018-04-25 under the name:

    funcfirmwareMode = 134

The same historical source contained the following commented SET command
template:

    00 77 86 00 00 00 00 00 00 00 00 00 00 00 00 00 00

This template can be interpreted as:

    00                         HID Report ID
    77                         SET opcode
    86                         Historical Firmware Mode selector
    00 00 00 00 00 00 00 00  Value equal to zero
    00 00 00 00 00 00        Trailer

No executable implementation, response parser, GUI action, or successful
hardware test for this command was found in the reviewed repository
history.

The command SET 0x86 has deliberately not been transmitted to the test
device. It could reset the device or place it in a firmware-update or
bootloader state.

It must not be tested until a documented recovery procedure exists.

## 12. Open questions

The following protocol questions remain unresolved:

1. Does SET selector 0x86 enter a bootloader or firmware-update mode?
2. What USB identity appears after entering that mode?
3. What is the purpose and format of selector 0x00?
4. Are SET commands acknowledged by the device?
5. Can trailer bytes contain information other than zero?
6. What other textual error messages can the firmware return?
7. Are selector definitions dependent on firmware version?
8. What are the valid limits for each writable parameter?
9. Does the device reject out-of-range values safely?
10. Is the report format identical on all hardware revisions?

## 13. Safety classification

The currently documented selectors are classified as follows:

| Selector | Classification |
|---|---|
| 0x81 | Normal operation |
| 0x82 | Normal operation |
| 0x83 | Normal operation within documented range |
| 0x84 | Normal operation with external-power precautions |
| 0x85 | Normal operation |
| 0x86 | Potentially disruptive; prohibited until recovery is defined |
| 0x00 | Unknown; prohibited until behavior is understood |

The Bias Tee must not be enabled when connected equipment cannot tolerate
DC voltage on the RF path.

## 14. Revision history

| Revision | Date | Description |
|---|---|---|
| 0.1 | 2026-08-02 | Initial experimentally grounded protocol specification |
