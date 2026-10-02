"""Corrupt real build artifacts to test failure modes, not just happy paths."""
import copy
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validation as v


class ValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = v.collect(v.ROOT)
        cls.map_text = (v.ROOT / "pokered.map").read_text()

    def parse(self, content):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.map"
            path.write_text(content)
            return v.parse_map(path)

    def test_missing_input(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(OSError):
                v.parse_map(Path(directory) / "missing.map")

    def test_truncated_map(self):
        with self.assertRaises(ValueError):
            self.parse(self.map_text.rsplit("TOTAL EMPTY:", 1)[0])

    def test_false_total(self):
        bad = re.sub(r"TOTAL EMPTY: \$[0-9a-f]+", "TOTAL EMPTY: $ffff", self.map_text, count=1)
        with self.assertRaises(ValueError):
            self.parse(bad)

    def test_omitted_range(self):
        with self.assertRaises(ValueError):
            self.parse(self.map_text.replace('SECTION: $0000-$0007 ($0008 bytes) ["rst0"]',
                                            'SECTION: $0001-$0007 ($0007 bytes) ["rst0"]'))

    def test_unknown_record(self):
        with self.assertRaises(ValueError):
            self.parse(self.map_text.replace("ROM0 bank #0:", "ROM0 bank #0:\nUNKNOWN: 123"))

    def test_duplicate_bank(self):
        with self.assertRaises(ValueError):
            self.parse(self.map_text + "\nROM0 bank #0:\n")

    def test_summary_disagreement(self):
        bad = re.sub(r"free in (\d+) banks", lambda m: f"free in {int(m[1]) + 1} banks",
                     self.map_text, count=1)
        with self.assertRaises(ValueError):
            self.parse(bad)

    def test_checksum_corruption(self):
        rom = bytearray((v.ROOT / "pokered.gbc").read_bytes())
        rom[0x200] ^= 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pokered.gbc"
            path.write_bytes(rom)
            with self.assertRaisesRegex(ValueError, "global checksum"):
                v.check_rom(path, self.report["pokered"]["banks"], {}, False)

    def test_fixture_leak(self):
        symbols = v.read_symbols(v.ROOT / "pokered.sym")
        symbols["WP004BattleFixture"] = (1, 0x4000)
        with self.assertRaisesRegex(ValueError, "isolation"):
            v.check_rom(v.ROOT / "pokered.gbc", self.report["pokered"]["banks"], symbols, False)

    def test_warning_not_hard_budget(self):
        report = copy.deepcopy(self.report)
        report["pokered"]["banks"]["WRAM0:00"]["free"] -= 1
        notices = v.warnings(report, self.report)
        self.assertEqual(len(notices), 1)
        self.assertIn("headroom shrank by 1", notices[0])

    def test_topology_requires_review(self):
        report = copy.deepcopy(self.report)
        del report["pokered"]["banks"]["ROMX:01"]
        with self.assertRaisesRegex(ValueError, "topology"):
            v.warnings(report, self.report)


if __name__ == "__main__":
    unittest.main()
