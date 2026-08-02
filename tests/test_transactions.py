import unittest
from collections.abc import Sequence

from openmorfeus.device import MoRFeusDevice
from openmorfeus.exceptions import ResponseTimeoutError
from openmorfeus.protocol import (
    Function,
    Opcode,
    build_report,
)
from openmorfeus.writable import WritableMoRFeusDevice


class SequenceTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.writes: list[bytes] = []
        self.nonblocking_history: list[int] = []
        self.closed = False

    def write(self, data: Sequence[int]) -> int:
        packet = bytes(data)
        self.writes.append(packet)
        return len(packet)

    def read(self, size: int):
        if not self.responses:
            return bytes()

        return self.responses.pop(0)[:size]

    def set_nonblocking(self, nonblocking: int) -> None:
        self.nonblocking_history.append(nonblocking)

    def close(self) -> None:
        self.closed = True


def response(
    opcode: Opcode,
    function: Function,
    value: int,
) -> bytes:
    return build_report(
        opcode,
        function,
        value,
        include_report_id=False,
    )


class CorrelatedResponseTests(unittest.TestCase):
    def test_get_ignores_stale_set_ack(self) -> None:
        transport = SequenceTransport([
            response(
                Opcode.SET,
                Function.FREQUENCY,
                1_300_000_000,
            ),
            response(
                Opcode.GET,
                Function.FREQUENCY,
                1_350_000_000,
            ),
        ])

        device = MoRFeusDevice(
            transport,
            response_timeout_s=0.020,
            poll_interval_s=0.0001,
        )

        value = device.get_frequency_hz()

        self.assertEqual(value, 1_350_000_000)
        self.assertEqual(
            transport.nonblocking_history,
            [1, 0],
        )

    def test_get_ignores_wrong_function(self) -> None:
        transport = SequenceTransport([
            response(
                Opcode.GET,
                Function.BIAS_TEE,
                0,
            ),
            response(
                Opcode.GET,
                Function.FREQUENCY,
                1_350_000_000,
            ),
        ])

        device = MoRFeusDevice(
            transport,
            response_timeout_s=0.020,
            poll_interval_s=0.0001,
        )

        self.assertEqual(
            device.get_frequency_hz(),
            1_350_000_000,
        )

    def test_timeout_restores_blocking_mode(self) -> None:
        transport = SequenceTransport([])

        device = MoRFeusDevice(
            transport,
            response_timeout_s=0.002,
            poll_interval_s=0.0001,
        )

        with self.assertRaises(ResponseTimeoutError):
            device.get_frequency_hz()

        self.assertEqual(
            transport.nonblocking_history,
            [1, 0],
        )

    def test_set_ignores_stale_get_before_ack(self) -> None:
        value = 1_350_000_000

        transport = SequenceTransport([
            response(
                Opcode.GET,
                Function.FREQUENCY,
                value,
            ),
            response(
                Opcode.SET,
                Function.FREQUENCY,
                value,
            ),
            response(
                Opcode.GET,
                Function.FREQUENCY,
                value,
            ),
        ])

        device = WritableMoRFeusDevice(
            transport,
            verification_delay_s=0,
            response_timeout_s=0.020,
            poll_interval_s=0.0001,
        )

        self.assertEqual(
            device.set_frequency_hz(value),
            value,
        )

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


if __name__ == "__main__":
    unittest.main()
