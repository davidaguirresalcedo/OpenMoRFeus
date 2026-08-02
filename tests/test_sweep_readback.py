import unittest

from openmorfeus.sweep import (
    SweepPlan,
    SweepProgress,
    run_sweep,
)


class QuantizedFakeDevice:
    """Fake device returning one hertz above requested values."""

    def __init__(self, initial_frequency_hz: int):
        self.initial_frequency_hz = initial_frequency_hz
        self.frequency_hz = initial_frequency_hz
        self.set_requests: list[int] = []

    def get_frequency_hz(self) -> int:
        return self.frequency_hz

    def set_frequency_hz(self, frequency_hz: int) -> int:
        self.set_requests.append(frequency_hz)

        # Restore the initial frequency exactly. During the sweep,
        # emulate the ±1 Hz quantization observed on the moRFeus.
        if frequency_hz == self.initial_frequency_hz:
            actual_frequency_hz = frequency_hz
        else:
            actual_frequency_hz = frequency_hz + 1

        self.frequency_hz = actual_frequency_hz
        return actual_frequency_hz


class SweepReadbackTests(unittest.TestCase):
    def test_progress_reports_verified_frequency(self) -> None:
        initial_frequency_hz = 1_350_000_000
        stop_frequency_hz = 1_351_000_000

        device = QuantizedFakeDevice(
            initial_frequency_hz
        )
        progress_events: list[SweepProgress] = []

        result = run_sweep(
            SweepPlan(
                start_hz=initial_frequency_hz,
                stop_hz=stop_frequency_hz,
                step_hz=1_000_000,
                dwell_s=0.0,
                restore_initial_frequency=True,
            ),
            device,
            on_progress=progress_events.append,
        )

        self.assertEqual(
            [event.frequency_hz for event in progress_events],
            [
                initial_frequency_hz,
                stop_frequency_hz + 1,
            ],
        )
        self.assertEqual(
            result.last_sweep_frequency_hz,
            stop_frequency_hz + 1,
        )
        self.assertTrue(
            result.restored_initial_frequency
        )
        self.assertEqual(
            device.frequency_hz,
            initial_frequency_hz,
        )


if __name__ == "__main__":
    unittest.main()
