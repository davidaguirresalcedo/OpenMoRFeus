import unittest
from unittest.mock import patch

from openmorfeus.device import (
    LcdTimeout,
    OperatingMode,
)
from openmorfeus.gui_controller import (
    GuiDeviceState,
    apply_state,
    read_state,
)


class FakeDevice:
    def __init__(
        self,
        state: GuiDeviceState,
    ):
        self.frequency_hz = state.frequency_hz
        self.mode = state.mode
        self.mixer_current = state.mixer_current
        self.bias_tee_enabled = (
            state.bias_tee_enabled
        )
        self.lcd_timeout = state.lcd_timeout
        self.set_calls = []

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return None

    def get_frequency_hz(self):
        return self.frequency_hz

    def get_mode(self):
        return self.mode

    def get_mixer_current(self):
        return self.mixer_current

    def get_bias_tee(self):
        return self.bias_tee_enabled

    def get_lcd_timeout(self):
        return self.lcd_timeout

    def set_frequency_hz(self, value):
        self.set_calls.append(("frequency", value))
        self.frequency_hz = value
        return value

    def set_mode(self, value):
        self.set_calls.append(("mode", value))
        self.mode = value
        return value

    def set_mixer_current(self, value):
        self.set_calls.append(
            ("mixer-current", value)
        )
        self.mixer_current = value
        return value

    def set_bias_tee(self, value):
        self.set_calls.append(("bias-tee", value))
        self.bias_tee_enabled = value
        return value

    def set_lcd_timeout(self, value):
        self.set_calls.append(
            ("lcd-timeout", value)
        )
        self.lcd_timeout = value
        return value


INITIAL_STATE = GuiDeviceState(
    frequency_hz=1_350_000_000,
    mode=OperatingMode.GENERATOR,
    mixer_current=0,
    bias_tee_enabled=False,
    lcd_timeout=LcdTimeout.ALWAYS_ON,
)


class GuiControllerTests(unittest.TestCase):
    def test_read_state(self):
        device = FakeDevice(INITIAL_STATE)

        with patch(
            "openmorfeus.gui_controller."
            "MoRFeusDevice.open",
            return_value=device,
        ):
            result = read_state(index=0)

        self.assertEqual(result, INITIAL_STATE)

    def test_unchanged_state_causes_no_writes(self):
        device = FakeDevice(INITIAL_STATE)

        with patch(
            "openmorfeus.gui_controller."
            "WritableMoRFeusDevice.open",
            return_value=device,
        ):
            result = apply_state(INITIAL_STATE)

        self.assertEqual(result, INITIAL_STATE)
        self.assertEqual(device.set_calls, [])

    def test_changed_state_is_applied(self):
        device = FakeDevice(INITIAL_STATE)

        desired = GuiDeviceState(
            frequency_hz=1_675_000_000,
            mode=OperatingMode.MIXER,
            mixer_current=3,
            bias_tee_enabled=True,
            lcd_timeout=LcdTimeout.TEN_SECONDS,
        )

        with patch(
            "openmorfeus.gui_controller."
            "WritableMoRFeusDevice.open",
            return_value=device,
        ):
            result = apply_state(desired)

        self.assertEqual(result, desired)
        self.assertEqual(
            device.set_calls,
            [
                ("frequency", 1_675_000_000),
                ("mode", OperatingMode.MIXER),
                ("mixer-current", 3),
                ("bias-tee", True),
                (
                    "lcd-timeout",
                    LcdTimeout.TEN_SECONDS,
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
