"""Encoding and decoding for the moRFeus USB HID protocol."""

from dataclasses import dataclass
from enum import IntEnum
from typing import TypeAlias


LOGICAL_REPORT_SIZE = 16
WRITE_BUFFER_SIZE = 17
REPORT_ID = 0x00
VALUE_SIZE = 8
TRAILER_SIZE = 6
MAX_UINT64 = (1 << 64) - 1


class ProtocolError(Exception):
    """Base exception for protocol-related errors."""


class ReportLengthError(ProtocolError):
    """Raised when a HID report has an unexpected length."""


class ResponseFormatError(ProtocolError):
    """Raised when a device response cannot be decoded."""


class Opcode(IntEnum):
    """Protocol operation codes."""

    GET = 0x72
    SET = 0x77


class Function(IntEnum):
    """Known moRFeus function selectors."""

    REGISTER = 0x00
    FREQUENCY = 0x81
    MIXER_GENERATOR = 0x82
    MIXER_CURRENT = 0x83
    BIAS_TEE = 0x84
    LCD_TIMEOUT = 0x85
    FIRMWARE_MODE = 0x86


@dataclass(frozen=True, slots=True)
class BinaryResponse:
    """Decoded binary response from the device."""

    opcode: int
    function: int
    value: int
    trailer: bytes
    raw: bytes


@dataclass(frozen=True, slots=True)
class TextResponse:
    """Decoded textual response, normally an error message."""

    message: str
    raw: bytes


Response: TypeAlias = BinaryResponse | TextResponse


def _validate_byte(name: str, value: int) -> int:
    if not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")

    if not 0 <= value <= 0xFF:
        raise ValueError(f"{name} must be between 0 and 255")

    return value


def _validate_uint64(value: int) -> int:
    if not isinstance(value, int):
        raise TypeError("value must be an integer")

    if not 0 <= value <= MAX_UINT64:
        raise ValueError("value must fit in an unsigned 64-bit integer")

    return value


def build_report(
    opcode: int | Opcode,
    function: int | Function,
    value: int = 0,
    *,
    include_report_id: bool = True,
) -> bytes:
    """Build a moRFeus HID command.

    The logical report contains 16 bytes:

        opcode + function + uint64 big-endian value + six-byte trailer

    hidapi writes require a leading Report ID byte equal to zero,
    resulting in a 17-byte host buffer.
    """

    opcode_value = _validate_byte("opcode", int(opcode))
    function_value = _validate_byte("function", int(function))
    numeric_value = _validate_uint64(value)

    logical_report = (
        bytes((opcode_value, function_value))
        + numeric_value.to_bytes(VALUE_SIZE, byteorder="big", signed=False)
        + bytes(TRAILER_SIZE)
    )

    if len(logical_report) != LOGICAL_REPORT_SIZE:
        raise AssertionError("internal report-construction error")

    if include_report_id:
        return bytes((REPORT_ID,)) + logical_report

    return logical_report


def decode_response(raw: bytes | bytearray | list[int]) -> Response:
    """Decode a 16-byte response returned by hidapi."""

    try:
        report = bytes(raw)
    except (TypeError, ValueError) as exc:
        raise ResponseFormatError("response is not a valid byte sequence") from exc

    if len(report) != LOGICAL_REPORT_SIZE:
        raise ReportLengthError(
            f"expected {LOGICAL_REPORT_SIZE} bytes, received {len(report)}"
        )

    if report[0] in (Opcode.GET, Opcode.SET):
        return BinaryResponse(
            opcode=report[0],
            function=report[1],
            value=int.from_bytes(
                report[2:10],
                byteorder="big",
                signed=False,
            ),
            trailer=report[10:16],
            raw=report,
        )

    text_payload = report.rstrip(b"\x00")

    if text_payload:
        try:
            message = text_payload.decode("ascii")
        except UnicodeDecodeError:
            message = ""

        if message and all(
            character.isprintable() or character in "\r\n\t"
            for character in message
        ):
            return TextResponse(message=message, raw=report)

    raise ResponseFormatError(
        "response is neither a recognized binary report nor printable ASCII"
    )
