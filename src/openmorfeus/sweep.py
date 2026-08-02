"""Safe frequency-sweep engine for OpenMoRFeus."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from .writable import (
    MAX_FREQUENCY_HZ,
    MIN_FREQUENCY_HZ,
    WritableMoRFeusDevice,
)


@dataclass(frozen=True, slots=True)
class SweepPlan:
    """Validated ascending frequency-sweep definition."""

    start_hz: int
    stop_hz: int
    step_hz: int
    dwell_s: float
    restore_initial_frequency: bool = True

    def __post_init__(self) -> None:
        for name, value in (
            ("start_hz", self.start_hz),
            ("stop_hz", self.stop_hz),
            ("step_hz", self.step_hz),
        ):
            if isinstance(value, bool) or not isinstance(
                value,
                int,
            ):
                raise TypeError(
                    f"{name} must be an integer"
                )

        if not (
            MIN_FREQUENCY_HZ
            <= self.start_hz
            <= MAX_FREQUENCY_HZ
        ):
            raise ValueError(
                "start_hz is outside the documented "
                "moRFeus frequency range"
            )

        if not (
            MIN_FREQUENCY_HZ
            <= self.stop_hz
            <= MAX_FREQUENCY_HZ
        ):
            raise ValueError(
                "stop_hz is outside the documented "
                "moRFeus frequency range"
            )

        if self.stop_hz < self.start_hz:
            raise ValueError(
                "stop_hz cannot be lower than start_hz"
            )

        if self.step_hz <= 0:
            raise ValueError(
                "step_hz must be positive"
            )

        if isinstance(self.dwell_s, bool) or not isinstance(
            self.dwell_s,
            (int, float),
        ):
            raise TypeError(
                "dwell_s must be numeric"
            )

        if self.dwell_s < 0:
            raise ValueError(
                "dwell_s cannot be negative"
            )

        if not isinstance(
            self.restore_initial_frequency,
            bool,
        ):
            raise TypeError(
                "restore_initial_frequency must be boolean"
            )

    @property
    def step_count(self) -> int:
        """Number of frequencies, including the final stop."""

        span = self.stop_hz - self.start_hz
        quotient, remainder = divmod(
            span,
            self.step_hz,
        )

        return (
            quotient
            + 1
            + (1 if remainder else 0)
        )

    @property
    def minimum_duration_s(self) -> float:
        """Dwell-only duration, excluding HID transactions."""

        return self.step_count * float(self.dwell_s)

    def frequency_at(self, index: int) -> int:
        """Return one planned frequency by zero-based index."""

        if not 0 <= index < self.step_count:
            raise IndexError(
                "sweep frequency index is out of range"
            )

        return min(
            self.start_hz + index * self.step_hz,
            self.stop_hz,
        )

    def frequencies(self) -> Iterator[int]:
        """Iterate without allocating a potentially large list."""

        for index in range(self.step_count):
            yield self.frequency_at(index)


@dataclass(frozen=True, slots=True)
class SweepProgress:
    """Progress reported after one verified frequency change."""

    step_number: int
    total_steps: int
    frequency_hz: int
    elapsed_s: float

    @property
    def percentage(self) -> float:
        return (
            self.step_number
            / self.total_steps
            * 100.0
        )


@dataclass(frozen=True, slots=True)
class SweepResult:
    """Final result of a completed or interrupted sweep."""

    completed: bool
    stopped: bool
    steps_completed: int
    total_steps: int
    initial_frequency_hz: int
    last_sweep_frequency_hz: int
    restored_initial_frequency: bool
    elapsed_s: float


class SweepControl:
    """Thread-safe pause, resume, and stop control."""

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._resume_event = threading.Event()
        self._resume_event.set()

    @property
    def stopped(self) -> bool:
        return self._stop_event.is_set()

    @property
    def paused(self) -> bool:
        return (
            not self._resume_event.is_set()
            and not self.stopped
        )

    def pause(self) -> None:
        if not self.stopped:
            self._resume_event.clear()

    def resume(self) -> None:
        if not self.stopped:
            self._resume_event.set()

    def stop(self) -> None:
        self._stop_event.set()

        # Release a worker waiting in paused state.
        self._resume_event.set()

    def wait_until_runnable(
        self,
        *,
        poll_interval_s: float = 0.05,
    ) -> bool:
        """Wait while paused and return False when stopped."""

        if poll_interval_s <= 0:
            raise ValueError(
                "poll_interval_s must be positive"
            )

        while not self.stopped:
            if self._resume_event.is_set():
                return True

            self._resume_event.wait(
                timeout=poll_interval_s
            )

        return False

    def wait_active_duration(
        self,
        duration_s: float,
        *,
        poll_interval_s: float = 0.02,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> bool:
        """Wait for active time, excluding time spent paused."""

        if duration_s < 0:
            raise ValueError(
                "duration_s cannot be negative"
            )

        if poll_interval_s <= 0:
            raise ValueError(
                "poll_interval_s must be positive"
            )

        remaining = float(duration_s)

        while remaining > 0:
            if not self.wait_until_runnable(
                poll_interval_s=poll_interval_s
            ):
                return False

            interval = min(
                poll_interval_s,
                remaining,
            )

            started = clock()
            sleeper(interval)
            elapsed = clock() - started

            if self.stopped:
                return False

            # Do not count a complete interval that ended paused.
            if self._resume_event.is_set():
                remaining -= (
                    elapsed
                    if elapsed > 0
                    else interval
                )

        return not self.stopped


def run_sweep(
    plan: SweepPlan,
    device: WritableMoRFeusDevice,
    *,
    control: SweepControl | None = None,
    on_progress: Callable[
        [SweepProgress],
        None,
    ] | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> SweepResult:
    """Run one sweep using an already-open writable device."""

    active_control = control or SweepControl()
    started = clock()

    initial_frequency_hz = (
        device.get_frequency_hz()
    )
    current_frequency_hz = initial_frequency_hz
    last_sweep_frequency_hz = initial_frequency_hz

    steps_completed = 0
    completed = False
    restored = False

    try:
        for step_number, frequency_hz in enumerate(
            plan.frequencies(),
            start=1,
        ):
            if not active_control.wait_until_runnable():
                break

            if frequency_hz != current_frequency_hz:
                device.set_frequency_hz(frequency_hz)
                current_frequency_hz = frequency_hz

            last_sweep_frequency_hz = frequency_hz
            steps_completed = step_number

            if on_progress is not None:
                on_progress(
                    SweepProgress(
                        step_number=step_number,
                        total_steps=plan.step_count,
                        frequency_hz=frequency_hz,
                        elapsed_s=clock() - started,
                    )
                )

            if not active_control.wait_active_duration(
                float(plan.dwell_s),
                clock=clock,
                sleeper=sleeper,
            ):
                break
        else:
            completed = True

    finally:
        if (
            plan.restore_initial_frequency
            and current_frequency_hz
            != initial_frequency_hz
        ):
            device.set_frequency_hz(
                initial_frequency_hz
            )
            restored = True

    return SweepResult(
        completed=completed,
        stopped=active_control.stopped,
        steps_completed=steps_completed,
        total_steps=plan.step_count,
        initial_frequency_hz=initial_frequency_hz,
        last_sweep_frequency_hz=(
            last_sweep_frequency_hz
        ),
        restored_initial_frequency=restored,
        elapsed_s=clock() - started,
    )


def execute_sweep(
    plan: SweepPlan,
    *,
    index: int = 0,
    response_timeout_s: float = 1.0,
    poll_interval_s: float = 0.005,
    control: SweepControl | None = None,
    on_progress: Callable[
        [SweepProgress],
        None,
    ] | None = None,
) -> SweepResult:
    """Open the selected moRFeus and execute one sweep."""

    with WritableMoRFeusDevice.open(
        index=index,
        response_timeout_s=response_timeout_s,
        poll_interval_s=poll_interval_s,
    ) as device:
        return run_sweep(
            plan,
            device,
            control=control,
            on_progress=on_progress,
        )
