"""Command-line interface for OpenMoRFeus."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .device import (
    LcdTimeout,
    MoRFeusDevice,
    OperatingMode,
)
from .exceptions import OpenMoRFeusError
from .writable import WritableMoRFeusDevice


_FREQUENCY_PATTERN = re.compile(
    r"^\s*"
    r"(?P<value>\d+(?:\.\d+)?)"
    r"\s*"
    r"(?P<unit>hz|khz|mhz|ghz)?"
    r"\s*$",
    re.IGNORECASE,
)

_FREQUENCY_MULTIPLIERS = {
    "hz": Decimal(1),
    "khz": Decimal(1_000),
    "mhz": Decimal(1_000_000),
    "ghz": Decimal(1_000_000_000),
}

_LCD_TIMEOUTS = {
    "always-on": LcdTimeout.ALWAYS_ON,
    "10s": LcdTimeout.TEN_SECONDS,
    "60s": LcdTimeout.SIXTY_SECONDS,
}


def parse_frequency_hz(text: str) -> int:
    """Parse a frequency with an optional unit.

    A value without an explicit unit is interpreted as MHz.
    Examples: 1350, 1350MHz, 1.35GHz, 1350000000Hz.
    """

    match = _FREQUENCY_PATTERN.fullmatch(text)

    if match is None:
        raise argparse.ArgumentTypeError(
            "invalid frequency; examples: "
            "1350MHz, 1.35GHz, or 1350000000Hz"
        )

    try:
        numeric_value = Decimal(match.group("value"))
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(
            "invalid numeric frequency"
        ) from exc

    unit = (match.group("unit") or "mhz").lower()
    frequency_hz = (
        numeric_value * _FREQUENCY_MULTIPLIERS[unit]
    ).to_integral_value(rounding=ROUND_HALF_UP)

    if frequency_hz <= 0:
        raise argparse.ArgumentTypeError(
            "frequency must be positive"
        )

    return int(frequency_hz)


def parse_positive_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "value must be numeric"
        ) from exc

    if value <= 0:
        raise argparse.ArgumentTypeError(
            "value must be positive"
        )

    return value


def parse_mixer_current(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "mixer current must be an integer from 0 to 7"
        ) from exc

    if not 0 <= value <= 7:
        raise argparse.ArgumentTypeError(
            "mixer current must be from 0 to 7"
        )

    return value


def parse_mode(text: str) -> OperatingMode:
    modes = {
        "mixer": OperatingMode.MIXER,
        "generator": OperatingMode.GENERATOR,
    }

    try:
        return modes[text.lower()]
    except KeyError as exc:
        raise argparse.ArgumentTypeError(
            "mode must be 'mixer' or 'generator'"
        ) from exc


def parse_on_off(text: str) -> bool:
    values = {
        "on": True,
        "off": False,
    }

    try:
        return values[text.lower()]
    except KeyError as exc:
        raise argparse.ArgumentTypeError(
            "value must be 'on' or 'off'"
        ) from exc


def parse_lcd_timeout(text: str) -> LcdTimeout:
    try:
        return _LCD_TIMEOUTS[text.lower()]
    except KeyError as exc:
        raise argparse.ArgumentTypeError(
            "LCD timeout must be "
            "'always-on', '10s', or '60s'"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openmorfeus",
        description=(
            "Read and configure an Outernet moRFeus "
            "through its USB HID interface."
        ),
    )

    parser.add_argument(
        "--index",
        type=int,
        default=0,
        help="device index when multiple moRFeus units are present",
    )
    parser.add_argument(
        "--timeout",
        type=parse_positive_float,
        default=0.50,
        help="transaction timeout in seconds (default: 0.50)",
    )
    parser.add_argument(
        "--poll-interval",
        type=parse_positive_float,
        default=0.005,
        help="HID polling interval in seconds (default: 0.005)",
    )

    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )

    commands.add_parser(
        "state",
        help="read the complete documented device state",
    )

    get_parser = commands.add_parser(
        "get",
        help="read one device setting",
    )
    get_parser.add_argument(
        "setting",
        choices=[
            "frequency",
            "mode",
            "mixer-current",
            "bias-tee",
            "lcd-timeout",
        ],
    )

    set_parser = commands.add_parser(
        "set",
        help="write and verify one device setting",
    )
    settings = set_parser.add_subparsers(
        dest="setting",
        required=True,
    )

    frequency_parser = settings.add_parser(
        "frequency",
        help="set the local-oscillator frequency",
    )
    frequency_parser.add_argument(
        "frequency_hz",
        type=parse_frequency_hz,
        metavar="FREQUENCY",
        help=(
            "frequency such as 1350MHz, 1.35GHz, "
            "or 1350000000Hz; bare values use MHz"
        ),
    )

    mode_parser = settings.add_parser(
        "mode",
        help="select Mixer or Generator mode",
    )
    mode_parser.add_argument(
        "mode",
        type=parse_mode,
        metavar="{mixer,generator}",
    )

    mixer_parser = settings.add_parser(
        "mixer-current",
        help="set the mixer current from 0 to 7",
    )
    mixer_parser.add_argument(
        "mixer_current",
        type=parse_mixer_current,
        metavar="0..7",
    )

    bias_parser = settings.add_parser(
        "bias-tee",
        help="enable or disable the Bias Tee",
    )
    bias_parser.add_argument(
        "enabled",
        type=parse_on_off,
        metavar="{on,off}",
    )

    lcd_parser = settings.add_parser(
        "lcd-timeout",
        help="set the LCD timeout",
    )
    lcd_parser.add_argument(
        "lcd_timeout",
        type=parse_lcd_timeout,
        metavar="{always-on,10s,60s}",
    )

    return parser


def _connection_arguments(
    args: argparse.Namespace,
) -> dict[str, int | float]:
    return {
        "index": args.index,
        "response_timeout_s": args.timeout,
        "poll_interval_s": args.poll_interval,
    }


def _print_state(device: MoRFeusDevice) -> None:
    frequency_hz = device.get_frequency_hz()
    mode = device.get_mode()
    mixer_current = device.get_mixer_current()
    bias_tee = device.get_bias_tee()
    lcd_timeout = device.get_lcd_timeout()

    print(
        f"Frequency     : "
        f"{frequency_hz / 1_000_000:.6f} MHz"
    )
    print(f"Mode          : {mode.name}")
    print(f"Mixer current : {mixer_current}")
    print(
        f"Bias Tee      : "
        f"{'ON' if bias_tee else 'OFF'}"
    )
    print(f"LCD timeout   : {lcd_timeout.name}")


def _run_get(args: argparse.Namespace) -> None:
    with MoRFeusDevice.open(
        **_connection_arguments(args)
    ) as device:
        if args.setting == "frequency":
            value = device.get_frequency_hz()
            print(f"{value / 1_000_000:.6f} MHz")

        elif args.setting == "mode":
            print(device.get_mode().name)

        elif args.setting == "mixer-current":
            print(device.get_mixer_current())

        elif args.setting == "bias-tee":
            print(
                "ON" if device.get_bias_tee() else "OFF"
            )

        elif args.setting == "lcd-timeout":
            print(device.get_lcd_timeout().name)


def _run_set(args: argparse.Namespace) -> None:
    with WritableMoRFeusDevice.open(
        **_connection_arguments(args)
    ) as device:
        if args.setting == "frequency":
            value = device.set_frequency_hz(
                args.frequency_hz
            )
            print(
                "Frequency set and verified: "
                f"{value / 1_000_000:.6f} MHz"
            )

        elif args.setting == "mode":
            value = device.set_mode(args.mode)
            print(
                "Mode set and verified: "
                f"{OperatingMode(value).name}"
            )

        elif args.setting == "mixer-current":
            value = device.set_mixer_current(
                args.mixer_current
            )
            print(
                "Mixer current set and verified: "
                f"{value}"
            )

        elif args.setting == "bias-tee":
            value = device.set_bias_tee(args.enabled)
            print(
                "Bias Tee set and verified: "
                f"{'ON' if value else 'OFF'}"
            )

        elif args.setting == "lcd-timeout":
            value = device.set_lcd_timeout(
                args.lcd_timeout
            )
            print(
                "LCD timeout set and verified: "
                f"{LcdTimeout(value).name}"
            )


def run(args: argparse.Namespace) -> None:
    if args.command == "state":
        with MoRFeusDevice.open(
            **_connection_arguments(args)
        ) as device:
            _print_state(device)
        return

    if args.command == "get":
        _run_get(args)
        return

    if args.command == "set":
        _run_set(args)
        return

    raise RuntimeError(
        f"unsupported command: {args.command}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        run(args)
    except (
        OpenMoRFeusError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        print(
            f"openmorfeus: error: {exc}",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print(
            "openmorfeus: interrupted",
            file=sys.stderr,
        )
        return 130

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
