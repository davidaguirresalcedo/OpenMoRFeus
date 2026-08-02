"""Read-only device driver for the Outernet moRFeus."""

import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Callable, Protocol, Sequence

from .exceptions import (
    DeviceError,
    DeviceNotFoundError,
    DeviceResponseError,
    UnexpectedResponseError,
    UnsupportedValueError,
)
from .protocol import (
    BinaryResponse,
    Function,
    Opcode,
    TextResponse,
    build_report,
    decode_response,
)


USB_VENDOR_ID = 0x10C4
USB_PRODUCT_ID = 0xEAC9
RESPONSE_SIZE = 16


class HidTransport(Protocol):
    """Minimum HID transport interface required by the driver."""

    def write(self, data: Sequence[int]) -> int | None:
        ...

    def read(self, size: int) -> Sequence[int]:
        ...

    def set_nonblocking(self, nonblocking: int) -> None:
        ...

    def close(self) -> None:
        ...


def _drain_pending_reports(
    transport: HidTransport,
    *,
    response_size: int = RESPONSE_SIZE,
    quiet_period_s: float = 0.20,
    hard_timeout_s: float = 1.00,
    poll_interval_s: float = 0.005,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> int:
    """Discard stale HID input reports before a new transaction."""

    if quiet_period_s < 0:
        raise ValueError("quiet_period_s cannot be negative")

    if hard_timeout_s < 0:
        raise ValueError("hard_timeout_s cannot be negative")

    if poll_interval_s <= 0:
        raise ValueError("poll_interval_s must be positive")

    drained = 0
    start = clock()
    quiet_since = start

    transport.set_nonblocking(1)

    try:
        while clock() - start < hard_timeout_s:
            pending = transport.read(response_size)
            now = clock()

            if pending:
                drained += 1
                quiet_since = now
                continue

            if now - quiet_since >= quiet_period_s:
                break

            sleeper(poll_interval_s)

    finally:
        transport.set_nonblocking(0)

    return drained


class OperatingMode(IntEnum):
    """Documented RF operating modes."""

    MIXER = 0
    GENERATOR = 1


class LcdTimeout(IntEnum):
    """Documented LCD timeout values."""

    ALWAYS_ON = 0
    TEN_SECONDS = 1
    SIXTY_SECONDS = 2


@dataclass(frozen=True, slots=True)
class DeviceState:
    """Read-only snapshot of the documented device state."""

    frequency_hz: int
    mode: OperatingMode
    mixer_current: int
    bias_tee_enabled: bool
    lcd_timeout: LcdTimeout

    @property
    def frequency_mhz(self) -> float:
        return self.frequency_hz / 1_000_000


class MoRFeusDevice:
    """Read-only interface to a physical moRFeus device."""

    def __init__(self, transport: HidTransport):
        self._transport = transport
        self._closed = False

    @classmethod
    def open(
        cls,
        *,
        vendor_id: int = USB_VENDOR_ID,
        product_id: int = USB_PRODUCT_ID,
        index: int = 0,
    ) -> "MoRFeusDevice":
        """Open a moRFeus through Python hidapi."""

        try:
            import hid
        except ImportError as exc:
            raise DeviceError(
                "Python package 'hid' is required for physical-device access"
            ) from exc

        devices: list[dict[str, Any]] = hid.enumerate(
            vendor_id,
            product_id,
        )

        if not devices:
            raise DeviceNotFoundError(
                "no moRFeus device was found"
            )

        if index < 0 or index >= len(devices):
            raise DeviceNotFoundError(
                f"device index {index} is unavailable; "
                f"{len(devices)} device(s) found"
            )

        path = devices[index].get("path")

        if not path:
            raise DeviceError(
                "hidapi enumeration did not provide a device path"
            )

        transport = hid.device()

        try:
            transport.open_path(path)
            _drain_pending_reports(transport)
        except Exception:
            transport.close()
            raise

        return cls(transport)

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        """Close the HID transport."""

        if not self._closed:
            self._transport.close()
            self._closed = True

    def __enter__(self) -> "MoRFeusDevice":
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _ensure_open(self) -> None:
        if self._closed:
            raise DeviceError("device is closed")

    def _get_value(self, function: Function) -> int:
        """Read one documented function value."""

        self._ensure_open()

        request = build_report(
            Opcode.GET,
            function,
            value=0,
        )

        written = self._transport.write(list(request))

        if written is not None and written != len(request):
            raise DeviceError(
                f"short HID write: expected {len(request)}, wrote {written}"
            )

        raw = self._transport.read(RESPONSE_SIZE)
        response = decode_response(raw)

        if isinstance(response, TextResponse):
            raise DeviceResponseError(response.message)

        if not isinstance(response, BinaryResponse):
            raise UnexpectedResponseError(
                "unexpected response type"
            )

        if response.opcode != Opcode.GET:
            raise UnexpectedResponseError(
                f"expected opcode 0x{Opcode.GET:02X}, "
                f"received 0x{response.opcode:02X}"
            )

        if response.function != function:
            raise UnexpectedResponseError(
                f"expected function 0x{function:02X}, "
                f"received 0x{response.function:02X}"
            )

        return response.value

    def get_frequency_hz(self) -> int:
        """Read the configured local-oscillator frequency in hertz."""

        return self._get_value(Function.FREQUENCY)

    def get_frequency_mhz(self) -> float:
        """Read the configured local-oscillator frequency in MHz."""

        return self.get_frequency_hz() / 1_000_000

    def get_mode(self) -> OperatingMode:
        """Read Mixer or Generator operating mode."""

        value = self._get_value(Function.MIXER_GENERATOR)

        try:
            return OperatingMode(value)
        except ValueError as exc:
            raise UnsupportedValueError(
                f"undocumented operating-mode value: {value}"
            ) from exc

    def get_mixer_current(self) -> int:
        """Read the mixer-current setting."""

        value = self._get_value(Function.MIXER_CURRENT)

        if not 0 <= value <= 7:
            raise UnsupportedValueError(
                f"undocumented mixer-current value: {value}"
            )

        return value

    def get_bias_tee(self) -> bool:
        """Read the Bias Tee state."""

        value = self._get_value(Function.BIAS_TEE)

        if value not in (0, 1):
            raise UnsupportedValueError(
                f"undocumented Bias Tee value: {value}"
            )

        return bool(value)

    def get_lcd_timeout(self) -> LcdTimeout:
        """Read the LCD timeout setting."""

        value = self._get_value(Function.LCD_TIMEOUT)

        try:
            return LcdTimeout(value)
        except ValueError as exc:
            raise UnsupportedValueError(
                f"undocumented LCD-timeout value: {value}"
            ) from exc

    def get_state(self) -> DeviceState:
        """Read all currently documented device-state values."""

        return DeviceState(
            frequency_hz=self.get_frequency_hz(),
            mode=self.get_mode(),
            mixer_current=self.get_mixer_current(),
            bias_tee_enabled=self.get_bias_tee(),
            lcd_timeout=self.get_lcd_timeout(),
        )
