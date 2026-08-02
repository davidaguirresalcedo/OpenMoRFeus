import unittest
from collections.abc import Sequence

from openmorfeus.device import (
    LcdTimeout,
    MoRFeusDevice,
    OperatingMode,
)
from openmorfeus.exceptions import (
    DeviceError,
    DeviceResponseError,
    UnexpectedResponseError,
    UnsupportedValueError,
)
from openmorfeus.protocol import (
    Function,
    Opcode,
    build_report,
)


class FakeTransport:
    def __init__(self, responses: list[bytes]):
        self.responses = list(responses)
        self.writes: list[bytes] = []
        self.closed = False

    def write(self, data: Sequence[int]) -> int:
        packet = bytes(data)
        self.writes.append(packet)
        return len(packet)

    def read(self, size: int) -> bytes:
        if not self.responses:
            return bytes()

        response = self.responses.pop(0)
        return response[:size]

    def close(self) -> None:
        self.closed = True


def binary_response(
    function: Function,
    value: int,
    *,
    opcode: Opcode = Opcode.GET,
) -> bytes:
    return build_report(
        opcode,
        function,
        value,
        include_report_id=False,
    )


class DeviceReadTests(unittest.TestCase):
    def test_get_frequency_hz(self) -> None:
        transport = FakeTransport([
            binary_response(
                Function.FREQUENCY,
                1_350_000_000,
            )
        ])
        device = MoRFeusDevice(transport)

        self.assertEqual(
            device.get_frequency_hz(),
            1_350_000_000,
        )
        self.assertEqual(
            transport.writes[0],
            build_report(
                Opcode.GET,
                Function.FREQUENCY,
                0,
            ),
        )

    def test_get_frequency_mhz(self) -> None:
        transport = FakeTransport([
            binary_response(
                Function.FREQUENCY,
                1_350_000_000,
            )
        ])
        device = MoRFeusDevice(transport)

        self.assertEqual(
            device.get_frequency_mhz(),
            1350.0,
        )

    def test_get_generator_mode(self) -> None:
        transport = FakeTransport([
            binary_response(
                Function.MIXER_GENERATOR,
                1,
            )
        ])
        device = MoRFeusDevice(transport)

        self.assertEqual(
            device.get_mode(),
            OperatingMode.GENERATOR,
        )

    def test_get_bias_tee_off(self) -> None:
        transport = FakeTransport([
            binary_response(
                Function.BIAS_TEE,
                0,
            )
        ])
        device = MoRFeusDevice(transport)

        self.assertFalse(device.get_bias_tee())

    def test_get_lcd_always_on(self) -> None:
        transport = FakeTransport([
            binary_response(
                Function.LCD_TIMEOUT,
                0,
            )
        ])
        device = MoRFeusDevice(transport)

        self.assertEqual(
            device.get_lcd_timeout(),
            LcdTimeout.ALWAYS_ON,
        )

    def test_text_error_is_raised(self) -> None:
        raw = bytes.fromhex(
            "49 6E 76 61 6C 69 64 20 "
            "70 61 72 61 6D 2E 00 00"
        )
        transport = FakeTransport([raw])
        device = MoRFeusDevice(transport)

        with self.assertRaisesRegex(
            DeviceResponseError,
            "Invalid param",
        ):
            device.get_frequency_hz()

    def test_unexpected_function_is_rejected(self) -> None:
        transport = FakeTransport([
            binary_response(
                Function.BIAS_TEE,
                0,
            )
        ])
        device = MoRFeusDevice(transport)

        with self.assertRaises(UnexpectedResponseError):
            device.get_frequency_hz()

    def test_invalid_mixer_current_is_rejected(self) -> None:
        transport = FakeTransport([
            binary_response(
                Function.MIXER_CURRENT,
                99,
            )
        ])
        device = MoRFeusDevice(transport)

        with self.assertRaises(UnsupportedValueError):
            device.get_mixer_current()

    def test_context_manager_closes_transport(self) -> None:
        transport = FakeTransport([])

        with MoRFeusDevice(transport):
            pass

        self.assertTrue(transport.closed)

    def test_closed_device_rejects_reads(self) -> None:
        transport = FakeTransport([])
        device = MoRFeusDevice(transport)
        device.close()

        with self.assertRaisesRegex(DeviceError, "closed"):
            device.get_frequency_hz()


if __name__ == "__main__":
    unittest.main()
