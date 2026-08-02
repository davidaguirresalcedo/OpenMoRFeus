"""Explicitly writable moRFeus driver with read-back verification."""

import time
from numbers import Real

from .device import (
    DEFAULT_POLL_INTERVAL_S,
    DEFAULT_RESPONSE_TIMEOUT_S,
    HidTransport,
    LcdTimeout,
    MoRFeusDevice,
    OperatingMode,
)
from .exceptions import (
    DeviceError,
    VerificationError,
)
from .protocol import (
    BinaryResponse,
    Function,
    Opcode,
    build_report,
)


MIN_FREQUENCY_HZ = 85_000_000
MAX_FREQUENCY_HZ = 5_400_000_000
FREQUENCY_VERIFICATION_TOLERANCE_HZ = 1
MIN_MIXER_CURRENT = 0
MAX_MIXER_CURRENT = 7


class WritableMoRFeusDevice(MoRFeusDevice):
    """moRFeus interface with explicit, validated SET operations.

    Every public write is followed by a GET operation that verifies
    the value returned by the physical device.

    No public method is provided for selector 0x86 or selector 0x00.
    """

    def __init__(
        self,
        transport: HidTransport,
        *,
        verification_delay_s: float = 0.05,
        response_timeout_s: float = DEFAULT_RESPONSE_TIMEOUT_S,
        poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
    ):
        super().__init__(
            transport,
            response_timeout_s=response_timeout_s,
            poll_interval_s=poll_interval_s,
        )

        if verification_delay_s < 0:
            raise ValueError(
                "verification_delay_s cannot be negative"
            )

        self._verification_delay_s = verification_delay_s
    def _write_value(
        self,
        function: Function,
        value: int,
    ) -> BinaryResponse:
        """Transmit one SET command and consume its acknowledgement."""

        self._ensure_open()

        request = build_report(
            Opcode.SET,
            function,
            value,
        )

        written = self._transport.write(list(request))

        if written is not None and written != len(request):
            raise DeviceError(
                f"short HID write: expected {len(request)}, "
                f"wrote {written}"
            )

        return self._read_expected_response(
            Opcode.SET,
            function,
        )
    def _set_and_verify(
        self,
        function: Function,
        value: int,
        *,
        tolerance: int = 0,
    ) -> int:
        """Write a value, consume its acknowledgement, and read it back."""

        if tolerance < 0:
            raise ValueError("tolerance cannot be negative")

        self._write_value(function, value)

        if self._verification_delay_s:
            time.sleep(self._verification_delay_s)

        actual = self._get_value(function)

        if abs(actual - value) > tolerance:
            raise VerificationError(
                f"verification failed for function "
                f"0x{function:02X}: requested {value}, "
                f"read back {actual}, tolerance ±{tolerance}"
            )

        return actual

    def set_frequency_hz(
        self,
        frequency_hz: int,
    ) -> int:
        """Set and verify the LO frequency in hertz."""

        if isinstance(frequency_hz, bool) or not isinstance(
            frequency_hz,
            int,
        ):
            raise TypeError(
                "frequency_hz must be an integer"
            )

        if not MIN_FREQUENCY_HZ <= frequency_hz <= MAX_FREQUENCY_HZ:
            raise ValueError(
                "frequency_hz must be between "
                f"{MIN_FREQUENCY_HZ} and {MAX_FREQUENCY_HZ}"
            )

        return self._set_and_verify(
            Function.FREQUENCY,
            frequency_hz,
            tolerance=FREQUENCY_VERIFICATION_TOLERANCE_HZ,
        )

    def set_frequency_mhz(
        self,
        frequency_mhz: Real,
    ) -> float:
        """Set and verify the LO frequency in megahertz."""

        if isinstance(frequency_mhz, bool) or not isinstance(
            frequency_mhz,
            Real,
        ):
            raise TypeError(
                "frequency_mhz must be a real number"
            )

        frequency_hz = round(
            float(frequency_mhz) * 1_000_000
        )

        verified_hz = self.set_frequency_hz(frequency_hz)
        return verified_hz / 1_000_000

    def set_mode(
        self,
        mode: OperatingMode | int,
    ) -> OperatingMode:
        """Set and verify Mixer or Generator mode."""

        if isinstance(mode, bool):
            raise TypeError(
                "mode must be an OperatingMode or integer"
            )

        try:
            requested = OperatingMode(mode)
        except ValueError as exc:
            raise ValueError(
                f"unsupported operating mode: {mode}"
            ) from exc

        actual = self._set_and_verify(
            Function.MIXER_GENERATOR,
            int(requested),
        )

        return OperatingMode(actual)

    def set_mixer_current(
        self,
        current: int,
    ) -> int:
        """Set and verify mixer current from 0 through 7."""

        if isinstance(current, bool) or not isinstance(current, int):
            raise TypeError(
                "current must be an integer"
            )

        if not MIN_MIXER_CURRENT <= current <= MAX_MIXER_CURRENT:
            raise ValueError(
                "current must be between "
                f"{MIN_MIXER_CURRENT} and {MAX_MIXER_CURRENT}"
            )

        return self._set_and_verify(
            Function.MIXER_CURRENT,
            current,
        )

    def set_bias_tee(
        self,
        enabled: bool,
    ) -> bool:
        """Set and verify the Bias Tee state."""

        if not isinstance(enabled, bool):
            raise TypeError(
                "enabled must be a boolean"
            )

        actual = self._set_and_verify(
            Function.BIAS_TEE,
            int(enabled),
        )

        return bool(actual)

    def set_lcd_timeout(
        self,
        timeout: LcdTimeout | int,
    ) -> LcdTimeout:
        """Set and verify the LCD timeout."""

        if isinstance(timeout, bool):
            raise TypeError(
                "timeout must be an LcdTimeout or integer"
            )

        try:
            requested = LcdTimeout(timeout)
        except ValueError as exc:
            raise ValueError(
                f"unsupported LCD timeout: {timeout}"
            ) from exc

        actual = self._set_and_verify(
            Function.LCD_TIMEOUT,
            int(requested),
        )

        return LcdTimeout(actual)
