import unittest

from openmorfeus.sweep import (
    SweepControl,
    SweepPlan,
    run_sweep,
)


class FakeWritableDevice:
    def __init__(self, frequency_hz: int):
        self.frequency_hz = frequency_hz
        self.set_calls: list[int] = []

    def get_frequency_hz(self) -> int:
        return self.frequency_hz

    def set_frequency_hz(
        self,
        frequency_hz: int,
    ) -> int:
        self.set_calls.append(frequency_hz)
        self.frequency_hz = frequency_hz
        return frequency_hz


class SweepPlanTests(unittest.TestCase):
    def test_exact_stop_frequency(self) -> None:
        plan = SweepPlan(
            start_hz=100_000_000,
            stop_hz=150_000_000,
            step_hz=25_000_000,
            dwell_s=0.5,
        )

        self.assertEqual(
            list(plan.frequencies()),
            [
                100_000_000,
                125_000_000,
                150_000_000,
            ],
        )
        self.assertEqual(plan.step_count, 3)
        self.assertEqual(
            plan.minimum_duration_s,
            1.5,
        )

    def test_non_divisible_span_includes_stop(
        self,
    ) -> None:
        plan = SweepPlan(
            start_hz=100_000_000,
            stop_hz=200_000_000,
            step_hz=30_000_000,
            dwell_s=0,
        )

        self.assertEqual(
            list(plan.frequencies()),
            [
                100_000_000,
                130_000_000,
                160_000_000,
                190_000_000,
                200_000_000,
            ],
        )

    def test_invalid_plans_are_rejected(self) -> None:
        cases = [
            {
                "start_hz": 200_000_000,
                "stop_hz": 100_000_000,
                "step_hz": 1_000_000,
                "dwell_s": 0,
            },
            {
                "start_hz": 100_000_000,
                "stop_hz": 200_000_000,
                "step_hz": 0,
                "dwell_s": 0,
            },
            {
                "start_hz": 100_000_000,
                "stop_hz": 200_000_000,
                "step_hz": 1_000_000,
                "dwell_s": -1,
            },
        ]

        for arguments in cases:
            with self.subTest(arguments=arguments):
                with self.assertRaises(ValueError):
                    SweepPlan(**arguments)


class SweepExecutionTests(unittest.TestCase):
    def test_complete_sweep_restores_initial_frequency(
        self,
    ) -> None:
        device = FakeWritableDevice(
            frequency_hz=150_000_000
        )
        progress = []

        plan = SweepPlan(
            start_hz=100_000_000,
            stop_hz=120_000_000,
            step_hz=10_000_000,
            dwell_s=0,
        )

        result = run_sweep(
            plan,
            device,
            on_progress=progress.append,
        )

        self.assertTrue(result.completed)
        self.assertFalse(result.stopped)
        self.assertEqual(result.steps_completed, 3)
        self.assertTrue(
            result.restored_initial_frequency
        )
        self.assertEqual(
            device.set_calls,
            [
                100_000_000,
                110_000_000,
                120_000_000,
                150_000_000,
            ],
        )
        self.assertEqual(
            [item.frequency_hz for item in progress],
            [
                100_000_000,
                110_000_000,
                120_000_000,
            ],
        )

    def test_stop_interrupts_and_restores(
        self,
    ) -> None:
        device = FakeWritableDevice(
            frequency_hz=150_000_000
        )
        control = SweepControl()

        plan = SweepPlan(
            start_hz=100_000_000,
            stop_hz=140_000_000,
            step_hz=10_000_000,
            dwell_s=0,
        )

        def stop_after_first(progress) -> None:
            if progress.step_number == 1:
                control.stop()

        result = run_sweep(
            plan,
            device,
            control=control,
            on_progress=stop_after_first,
        )

        self.assertFalse(result.completed)
        self.assertTrue(result.stopped)
        self.assertEqual(result.steps_completed, 1)
        self.assertEqual(
            device.set_calls,
            [
                100_000_000,
                150_000_000,
            ],
        )

    def test_restore_can_be_disabled(self) -> None:
        device = FakeWritableDevice(
            frequency_hz=150_000_000
        )

        plan = SweepPlan(
            start_hz=100_000_000,
            stop_hz=120_000_000,
            step_hz=10_000_000,
            dwell_s=0,
            restore_initial_frequency=False,
        )

        result = run_sweep(plan, device)

        self.assertTrue(result.completed)
        self.assertFalse(
            result.restored_initial_frequency
        )
        self.assertEqual(
            device.frequency_hz,
            120_000_000,
        )
        self.assertEqual(
            device.set_calls,
            [
                100_000_000,
                110_000_000,
                120_000_000,
            ],
        )


if __name__ == "__main__":
    unittest.main()
