import unittest
from collections.abc import Sequence

from openmorfeus.device import (
    LcdTimeout,
    OperatingMode,
)
from openmorfeus.exceptions import VerificationError
from openmorfeus.protocol import (
    Function,
    Opcode,
    build_report,
)
from openmorfeus.writable import WritableMoRFeusDevice


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

        return self.responses.pop(0)[:size]

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


def set_ack(
    function: Function,
    value: int,
) -> bytes:
    return binary_response(
        function,
        value,
        opcode=Opcode.SET,
    )


class WritableDeviceTests(unittest.TestCase):
    def make_device(
        self,
        responses: list[bytes],
    ) -> tuple[WritableMoRFeusDevice, FakeTransport]:
        transport = FakeTransport(responses)
        device = WritableMoRFeusDevice(
            transport,
            verification_delay_s=0,
        )
        return device, transport

    def test_set_frequency_is_verified(self) -> None:
        value = 1_350_000_000

        device, transport = self.make_device([
            set_ack(Function.FREQUENCY, value),
            binary_response(Function.FREQUENCY, value),
        ])

        result = device.set_frequency_hz(value)

        self.assertEqual(result, value)
        self.assertEqual(
            transport.writes,
            [
                build_report(
                    Opcode.SET,
                    Function.FREQUENCY,
                    value,
                ),
                build_report(
                    Opcode.GET,
                    Function.FREQUENCY,
                    0,
                ),
            ],
        )

    def test_set_frequency_mhz(self) -> None:
        value = 1_675_000_000

        device, _ = self.make_device([
            set_ack(Function.FREQUENCY, value),
            binary_response(Function.FREQUENCY, value),
        ])

        self.assertEqual(
            device.set_frequency_mhz(1675),
            1675.0,
        )

    def test_frequency_out_of_range_is_rejected(self) -> None:
        device, transport = self.make_device([])

        with self.assertRaises(ValueError):
            device.set_frequency_hz(84_999_999)

        self.assertEqual(transport.writes, [])

    def test_set_generator_mode(self) -> None:
        device, transport = self.make_device([
            set_ack(Function.MIXER_GENERATOR, 1),
            binary_response(Function.MIXER_GENERATOR, 1),
        ])

        result = device.set_mode(
            OperatingMode.GENERATOR
        )

        self.assertEqual(
            result,
            OperatingMode.GENERATOR,
        )
        self.assertEqual(
            transport.writes[0],
            build_report(
                Opcode.SET,
                Function.MIXER_GENERATOR,
                1,
            ),
        )

    def test_invalid_mixer_current_is_rejected(self) -> None:
        device, transport = self.make_device([])

        with self.assertRaises(ValueError):
            device.set_mixer_current(8)

        self.assertEqual(transport.writes, [])

    def test_bias_tee_requires_boolean(self) -> None:
        device, transport = self.make_device([])

        with self.assertRaises(TypeError):
            device.set_bias_tee(1)

        self.assertEqual(transport.writes, [])

    def test_set_bias_tee_off(self) -> None:
        device, _ = self.make_device([
            set_ack(Function.BIAS_TEE, 0),
            binary_response(Function.BIAS_TEE, 0),
        ])

        self.assertFalse(
            device.set_bias_tee(False)
        )

    def test_set_lcd_timeout(self) -> None:
        device, _ = self.make_device([
            set_ack(Function.LCD_TIMEOUT, 2),
            binary_response(Function.LCD_TIMEOUT, 2),
        ])

        result = device.set_lcd_timeout(
            LcdTimeout.SIXTY_SECONDS
        )

        self.assertEqual(
            result,
            LcdTimeout.SIXTY_SECONDS,
        )

    def test_readback_mismatch_is_rejected(self) -> None:
        requested = 1_350_000_000

        device, _ = self.make_device([
            set_ack(Function.FREQUENCY, requested),
            binary_response(
                Function.FREQUENCY,
                1_349_000_000,
            ),
        ])

        with self.assertRaisesRegex(
            VerificationError,
            "verification failed",
        ):
            device.set_frequency_hz(requested)


if __name__ == "__main__":
    unittest.main()
