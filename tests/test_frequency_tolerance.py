import unittest
from collections.abc import Sequence

from openmorfeus.exceptions import VerificationError
from openmorfeus.protocol import Function, Opcode, build_report
from openmorfeus.writable import WritableMoRFeusDevice


class FakeTransport:
    def __init__(self, responses: list[bytes]):
        self.responses = list(responses)
        self.writes: list[bytes] = []
        self.nonblocking_history: list[int] = []

    def write(self, data: Sequence[int]) -> int:
        packet = bytes(data)
        self.writes.append(packet)
        return len(packet)

    def read(self, size: int) -> bytes:
        if not self.responses:
            return bytes()

        return self.responses.pop(0)[:size]

    def set_nonblocking(self, value: int) -> None:
        self.nonblocking_history.append(value)

    def close(self) -> None:
        pass


def response(
    opcode: Opcode,
    value: int,
) -> bytes:
    return build_report(
        opcode,
        Function.FREQUENCY,
        value,
        include_report_id=False,
    )


class FrequencyToleranceTests(unittest.TestCase):
    def test_one_hertz_difference_is_accepted(self) -> None:
        requested = 1_352_000_000
        actual = requested + 1

        transport = FakeTransport([
            response(Opcode.SET, requested),
            response(Opcode.GET, actual),
        ])

        device = WritableMoRFeusDevice(
            transport,
            verification_delay_s=0,
            response_timeout_s=0.020,
            poll_interval_s=0.0001,
        )

        self.assertEqual(
            device.set_frequency_hz(requested),
            actual,
        )

    def test_two_hertz_difference_is_rejected(self) -> None:
        requested = 1_352_000_000
        actual = requested + 2

        transport = FakeTransport([
            response(Opcode.SET, requested),
            response(Opcode.GET, actual),
        ])

        device = WritableMoRFeusDevice(
            transport,
            verification_delay_s=0,
            response_timeout_s=0.020,
            poll_interval_s=0.0001,
        )

        with self.assertRaises(VerificationError):
            device.set_frequency_hz(requested)


if __name__ == "__main__":
    unittest.main()
