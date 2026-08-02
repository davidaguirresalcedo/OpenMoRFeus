import unittest

from openmorfeus.protocol import (
    BinaryResponse,
    Function,
    Opcode,
    ReportLengthError,
    TextResponse,
    build_report,
    decode_response,
)


class BuildReportTests(unittest.TestCase):
    def test_get_frequency_request(self) -> None:
        report = build_report(
            Opcode.GET,
            Function.FREQUENCY,
            0,
        )

        expected = bytes.fromhex(
            "00 72 81 "
            "00 00 00 00 00 00 00 00 "
            "00 00 00 00 00 00"
        )

        self.assertEqual(report, expected)
        self.assertEqual(len(report), 17)

    def test_set_frequency_1350_mhz(self) -> None:
        report = build_report(
            Opcode.SET,
            Function.FREQUENCY,
            1_350_000_000,
        )

        expected = bytes.fromhex(
            "00 77 81 "
            "00 00 00 00 50 77 5D 80 "
            "00 00 00 00 00 00"
        )

        self.assertEqual(report, expected)

    def test_logical_report_without_report_id(self) -> None:
        report = build_report(
            Opcode.GET,
            Function.BIAS_TEE,
            0,
            include_report_id=False,
        )

        self.assertEqual(len(report), 16)
        self.assertEqual(report[:2], bytes.fromhex("72 84"))


class DecodeResponseTests(unittest.TestCase):
    def test_decode_frequency_response(self) -> None:
        raw = bytes.fromhex(
            "72 81 "
            "00 00 00 00 50 77 5D 80 "
            "00 00 00 00 00 00"
        )

        response = decode_response(raw)

        self.assertIsInstance(response, BinaryResponse)
        self.assertEqual(response.opcode, Opcode.GET)
        self.assertEqual(response.function, Function.FREQUENCY)
        self.assertEqual(response.value, 1_350_000_000)
        self.assertEqual(response.trailer, bytes(6))

    def test_decode_invalid_param_text(self) -> None:
        raw = bytes.fromhex(
            "49 6E 76 61 6C 69 64 20 "
            "70 61 72 61 6D 2E 00 00"
        )

        response = decode_response(raw)

        self.assertIsInstance(response, TextResponse)
        self.assertEqual(response.message, "Invalid param.")

    def test_reject_invalid_length(self) -> None:
        with self.assertRaises(ReportLengthError):
            decode_response(bytes(15))


if __name__ == "__main__":
    unittest.main()
