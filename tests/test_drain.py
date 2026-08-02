import unittest
from collections.abc import Sequence

from openmorfeus.device import _drain_pending_reports


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class DrainTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.nonblocking_history = []

    def write(self, data: Sequence[int]) -> int:
        return len(data)

    def read(self, size: int):
        if not self.responses:
            return bytes()

        response = self.responses.pop(0)

        if isinstance(response, Exception):
            raise response

        return response[:size]

    def set_nonblocking(self, nonblocking: int) -> None:
        self.nonblocking_history.append(nonblocking)

    def close(self) -> None:
        pass


class DrainPendingReportsTests(unittest.TestCase):
    def test_stale_reports_are_drained(self) -> None:
        clock = FakeClock()
        transport = DrainTransport([
            bytes.fromhex(
                "77 81 00 00 00 00 50 77 "
                "5D 80 00 00 00 00 00 00"
            ),
            bytes.fromhex(
                "72 81 00 00 00 00 50 77 "
                "5D 80 00 00 00 00 00 00"
            ),
        ])

        drained = _drain_pending_reports(
            transport,
            quiet_period_s=0.020,
            hard_timeout_s=0.100,
            poll_interval_s=0.005,
            clock=clock.monotonic,
            sleeper=clock.sleep,
        )

        self.assertEqual(drained, 2)
        self.assertEqual(
            transport.nonblocking_history,
            [1, 0],
        )
        self.assertGreaterEqual(clock.now, 0.020)

    def test_blocking_mode_restored_after_error(self) -> None:
        clock = FakeClock()
        transport = DrainTransport([
            RuntimeError("simulated HID read failure"),
        ])

        with self.assertRaisesRegex(
            RuntimeError,
            "simulated HID read failure",
        ):
            _drain_pending_reports(
                transport,
                quiet_period_s=0.020,
                hard_timeout_s=0.100,
                poll_interval_s=0.005,
                clock=clock.monotonic,
                sleeper=clock.sleep,
            )

        self.assertEqual(
            transport.nonblocking_history,
            [1, 0],
        )


if __name__ == "__main__":
    unittest.main()
