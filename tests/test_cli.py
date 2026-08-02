import argparse
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from openmorfeus.cli import main, parse_frequency_hz
from openmorfeus.device import LcdTimeout, OperatingMode
from openmorfeus.exceptions import DeviceError


class FakeDevice:
    def __init__(self):
        self.frequency_hz = 1_350_000_000
        self.mode = OperatingMode.GENERATOR
        self.mixer_current = 0
        self.bias_tee = False
        self.lcd_timeout = LcdTimeout.ALWAYS_ON

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
        return self.bias_tee

    def get_lcd_timeout(self):
        return self.lcd_timeout

    def set_frequency_hz(self, value):
        self.frequency_hz = value
        return value

    def set_mode(self, value):
        self.mode = value
        return value

    def set_mixer_current(self, value):
        self.mixer_current = value
        return value

    def set_bias_tee(self, value):
        self.bias_tee = value
        return value

    def set_lcd_timeout(self, value):
        self.lcd_timeout = value
        return value


class FrequencyParserTests(unittest.TestCase):
    def test_parse_mhz(self):
        self.assertEqual(
            parse_frequency_hz("1350MHz"),
            1_350_000_000,
        )

    def test_parse_ghz(self):
        self.assertEqual(
            parse_frequency_hz("1.35GHz"),
            1_350_000_000,
        )

    def test_bare_frequency_defaults_to_mhz(self):
        self.assertEqual(
            parse_frequency_hz("1350"),
            1_350_000_000,
        )

    def test_invalid_frequency_is_rejected(self):
        with self.assertRaises(
            argparse.ArgumentTypeError
        ):
            parse_frequency_hz("not-a-frequency")


class CliDispatchTests(unittest.TestCase):
    def test_state_command(self):
        device = FakeDevice()
        output = io.StringIO()

        with patch(
            "openmorfeus.cli.MoRFeusDevice.open",
            return_value=device,
        ):
            with redirect_stdout(output):
                result = main(["state"])

        self.assertEqual(result, 0)
        self.assertIn(
            "1350.000000 MHz",
            output.getvalue(),
        )
        self.assertIn(
            "GENERATOR",
            output.getvalue(),
        )
        self.assertIn(
            "Bias Tee      : OFF",
            output.getvalue(),
        )

    def test_get_mode(self):
        device = FakeDevice()
        output = io.StringIO()

        with patch(
            "openmorfeus.cli.MoRFeusDevice.open",
            return_value=device,
        ):
            with redirect_stdout(output):
                result = main(["get", "mode"])

        self.assertEqual(result, 0)
        self.assertEqual(
            output.getvalue().strip(),
            "GENERATOR",
        )

    def test_set_frequency(self):
        device = FakeDevice()
        output = io.StringIO()

        with patch(
            "openmorfeus.cli."
            "WritableMoRFeusDevice.open",
            return_value=device,
        ):
            with redirect_stdout(output):
                result = main([
                    "set",
                    "frequency",
                    "1675MHz",
                ])

        self.assertEqual(result, 0)
        self.assertEqual(
            device.frequency_hz,
            1_675_000_000,
        )
        self.assertIn(
            "1675.000000 MHz",
            output.getvalue(),
        )

    def test_set_bias_tee(self):
        device = FakeDevice()
        output = io.StringIO()

        with patch(
            "openmorfeus.cli."
            "WritableMoRFeusDevice.open",
            return_value=device,
        ):
            with redirect_stdout(output):
                result = main([
                    "set",
                    "bias-tee",
                    "on",
                ])

        self.assertEqual(result, 0)
        self.assertTrue(device.bias_tee)
        self.assertIn(
            "Bias Tee set and verified: ON",
            output.getvalue(),
        )

    def test_device_error_returns_one(self):
        error_output = io.StringIO()

        with patch(
            "openmorfeus.cli.MoRFeusDevice.open",
            side_effect=DeviceError(
                "simulated device failure"
            ),
        ):
            with redirect_stderr(error_output):
                result = main(["state"])

        self.assertEqual(result, 1)
        self.assertIn(
            "simulated device failure",
            error_output.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
