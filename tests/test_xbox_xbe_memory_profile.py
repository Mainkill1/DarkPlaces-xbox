"""The release XBE memory flag is profile-specific despite cxbe's fixed default."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "xbox" / "set_xbe_memory_profile.py"


class XbeMemoryProfileTests(unittest.TestCase):
    def test_changes_only_limit_bit_and_is_reversible(self):
        with tempfile.TemporaryDirectory() as directory:
            xbe = Path(directory) / "default.xbe"
            original = bytearray(b"XBEH" + b"\xa5" * 4092)
            original[0x124:0x128] = (0x5).to_bytes(4, "little")
            xbe.write_bytes(original)
            for profile, expected in (("dev128", 0x1), ("stock64", 0x5)):
                run = subprocess.run(
                    [sys.executable, str(TOOL), str(xbe), profile],
                    capture_output=True, text=True,
                )
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                changed = xbe.read_bytes()
                self.assertEqual(int.from_bytes(changed[0x124:0x128], "little"), expected)
                self.assertEqual(changed[:0x124], original[:0x124])
                self.assertEqual(changed[0x128:], original[0x128:])

    def test_rejects_unexpected_header_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            xbe = Path(directory) / "default.xbe"
            original = bytearray(b"XBEH" + b"\x00" * 4092)
            original[0x124:0x128] = (0x9).to_bytes(4, "little")
            xbe.write_bytes(original)
            run = subprocess.run(
                [sys.executable, str(TOOL), str(xbe), "dev128"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(xbe.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
