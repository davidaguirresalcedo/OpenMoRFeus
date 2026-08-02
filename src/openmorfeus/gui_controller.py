"""Hardware controller used by the optional graphical interface."""

from dataclasses import dataclass

from .device import (
    LcdTimeout,
    MoRFeusDevice,
    OperatingMode,
)
from .writable import WritableMoRFeusDevice


@dataclass(frozen=True, slots=True)
class GuiDeviceState:
    """Documented moRFeus state presented by the GUI."""

    frequency_hz: int
    mode: OperatingMode
    mixer_current: int
    bias_tee_enabled: bool
    lcd_timeout: LcdTimeout


def read_device_state(
    device: MoRFeusDevice,
) -> GuiDeviceState:
    """Read all documented settings from an open device."""

    return GuiDeviceState(
        frequency_hz=device.get_frequency_hz(),
        mode=device.get_mode(),
        mixer_current=device.get_mixer_current(),
        bias_tee_enabled=device.get_bias_tee(),
        lcd_timeout=device.get_lcd_timeout(),
    )


def read_state(
    *,
    index: int = 0,
    response_timeout_s: float = 1.0,
    poll_interval_s: float = 0.005,
) -> GuiDeviceState:
    """Open a device and return its documented state."""

    with MoRFeusDevice.open(
        index=index,
        response_timeout_s=response_timeout_s,
        poll_interval_s=poll_interval_s,
    ) as device:
        return read_device_state(device)


def apply_state(
    desired: GuiDeviceState,
    *,
    index: int = 0,
    response_timeout_s: float = 1.0,
    poll_interval_s: float = 0.005,
) -> GuiDeviceState:
    """Apply changed settings and return verified state.

    The physical state is read before writing. Settings that already
    match the requested values are not transmitted again.
    """

    with WritableMoRFeusDevice.open(
        index=index,
        response_timeout_s=response_timeout_s,
        poll_interval_s=poll_interval_s,
    ) as device:
        current = read_device_state(device)

        if desired.frequency_hz != current.frequency_hz:
            device.set_frequency_hz(desired.frequency_hz)

        if desired.mode != current.mode:
            device.set_mode(desired.mode)

        if desired.mixer_current != current.mixer_current:
            device.set_mixer_current(desired.mixer_current)

        if (
            desired.bias_tee_enabled
            != current.bias_tee_enabled
        ):
            device.set_bias_tee(
                desired.bias_tee_enabled
            )

        if desired.lcd_timeout != current.lcd_timeout:
            device.set_lcd_timeout(
                desired.lcd_timeout
            )

        return read_device_state(device)
