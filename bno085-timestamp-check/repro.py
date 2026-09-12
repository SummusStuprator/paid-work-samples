"""Hardware-free timestamp contract checks against one pinned upstream driver.

The caller supplies the source file. No network, full driver import, GPIO,
serial access, source modification, or device initialization occurs.
"""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest


SOURCE_COMMIT = "3434f59998d3c8cf0036dd5a9e4b8b5c0a1e2cdf"
SOURCE_SHA256_LF = "31b32dcd31f495dc6977f3a23c7a1d025c391c912081be763e1bdeb306e5ae70"


def load_methods(source_path):
    # Git can check text out with CRLF on Windows. Only normalize CRLF to LF;
    # any other byte change is rejected before parsing or executing source.
    source_bytes = source_path.read_bytes().replace(b"\r\n", b"\n")
    digest = hashlib.sha256(source_bytes).hexdigest()
    if digest != SOURCE_SHA256_LF:
        raise ValueError(
            "Source hash differs from the pinned driver (after CRLF-to-LF "
            f"normalization). Expected {SOURCE_SHA256_LF}, got {digest}."
        )
    tree = ast.parse(source_bytes.decode("utf-8"), filename="pinned_bno08x.py")
    cls = next(node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == "BNO08X")
    names = {"update_sensors", "_process_report"}
    methods = [node for node in cls.body
               if isinstance(node, ast.FunctionDef) and node.name in names]
    if {method.name for method in methods} != names:
        raise ValueError("Pinned source is missing the expected methods.")
    for method in methods:
        method.decorator_list = []
    env = {
        # These small fixtures never wrap MicroPython's clock.
        "ticks_diff": lambda end, start: end - start,
        # Only fixture IDs, with lengths/scaling copied from the pinned source.
        "_REPORT_LENGTHS": {0xFB: 5, 0xFA: 5, 0x05: 14},
        "_SENSOR_SCALING": {0x05: (2 ** -14, 4)},
        "_BASE_TIMESTAMP": 0xFB,
        "_TIMESTAMP_REBASE": 0xFA,
    }
    module = ast.Module(body=methods, type_ignores=[])
    exec(compile(module, "pinned_bno08x.py", "exec"), env)
    return env


def rotation_report(delay_ticks):
    if not 0 <= delay_ticks <= 0x3FFF:
        raise ValueError("Report delay must fit the SH-2 14-bit field.")
    header = bytes((0x05, 0, ((delay_ticks >> 8) << 2) | 3, delay_ticks & 0xFF))
    # SH-2 order i,j,k,real: a stationary identity quaternion and accuracy angle.
    # Only the resulting report timestamp is inspected.
    return header + struct.pack("<hhhhH", 0, 0, 0, 16384, 0)


def timestamp_ms(methods, base_ticks, rebase_ticks=None, delay_ticks=0):
    payload = struct.pack("<Bi", 0xFB, base_ticks)
    if rebase_ticks is not None:
        payload += struct.pack("<Bi", 0xFA, rebase_ticks)
    payload += rotation_report(delay_ticks)
    driver = SimpleNamespace(
        _new_data_interrupt=True,
        _report_values={},
        _unread_report_count={0x05: 0},
        ms_at_interrupt=5000,
        _epoch_start_ms=0,
        _last_base_timestamp_us=0,
    )
    driver._read_packet = lambda wait: (payload, 3, len(payload))
    driver._process_report = lambda report_id, data: methods["_process_report"](
        driver, report_id, data
    )
    methods["update_sensors"](driver)
    return driver._report_values[0x05][-1]


def observations(methods):
    cases = [
        ("zero base control", 0, None, 0, 5000),
        ("positive base control", 40000, None, 10000, 2000),
        ("signed base delta", -10, None, 0, 5001),
        ("manufacturer positive rebase example", 40000, 15000, 10000, 3500),
    ]
    results = []
    for label, base, rebase, delay, expected in cases:
        observed = timestamp_ms(methods, base, rebase, delay)
        results.append({
            "case": label,
            "base_ticks": base,
            "rebase_ticks": rebase,
            "delay_ticks": delay,
            "expected_ms": expected,
            "upstream_ms": observed,
            "matches_contract": abs(observed - expected) < 0.000001,
        })
    return {
        "source_commit": SOURCE_COMMIT,
        "source_sha256_after_crlf_to_lf": SOURCE_SHA256_LF,
        "synthetic_data_only": True,
        "hardware_tested": False,
        "host_interrupt_ms": 5000,
        "tick_unit_microseconds": 100,
        "results": results,
    }


def contract_suite(methods):
    class TimestampContracts(unittest.TestCase):
        def test_zero_base_control(self):
            self.assertAlmostEqual(timestamp_ms(methods, 0), 5000)

        def test_positive_base_control(self):
            self.assertAlmostEqual(timestamp_ms(methods, 40000, delay_ticks=10000), 2000)

        def test_signed_base_delta(self):
            self.assertAlmostEqual(timestamp_ms(methods, -10), 5001)

        def test_manufacturer_positive_rebase_example(self):
            self.assertAlmostEqual(timestamp_ms(methods, 40000, 15000, 10000), 3500)

    return unittest.defaultTestLoader.loadTestsFromTestCase(TimestampContracts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="Local lib/bno08x.py from the pinned upstream commit")
    parser.add_argument("--observe", action="store_true",
                        help="Print expected/observed JSON without running unittest")
    args = parser.parse_args()
    try:
        methods = load_methods(args.source)
    except (OSError, ValueError, UnicodeError) as error:
        parser.error(str(error))
    if args.observe:
        print(json.dumps(observations(methods), indent=2))
        return 0
    result = unittest.TextTestRunner(verbosity=2).run(contract_suite(methods))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
