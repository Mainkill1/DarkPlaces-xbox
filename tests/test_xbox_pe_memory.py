"""Tests for the stock-memory PE image gate."""

from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "tools" / "xbox" / "verify_xbox_pe_memory.py"


def write_pe(path: Path, image_size: int) -> None:
    data = bytearray(0x200)
    data[0:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", data, 0x98, 0x10B)
    struct.pack_into("<I", data, 0x98 + 56, image_size)
    path.write_bytes(data)


class XboxPeMemoryTests(unittest.TestCase):
    def run_bytes(self, data: bytes) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "main.exe"
            executable.write_bytes(data)
            return subprocess.run(
                [sys.executable, str(VERIFIER), str(executable)],
                capture_output=True,
                text=True,
                timeout=30,
            )

    def run_verifier(self, image_size: int) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "main.exe"
            write_pe(executable, image_size)
            return subprocess.run(
                [sys.executable, str(VERIFIER), str(executable)],
                capture_output=True,
                text=True,
                timeout=30,
            )

    def test_accepts_image_at_stock_profile_limit(self):
        proc = self.run_verifier(24 * 1024 * 1024)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_rejects_image_above_stock_profile_limit(self):
        proc = self.run_verifier(24 * 1024 * 1024 + 4096)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("exceeds 25165824-byte limit", proc.stderr)

    def test_rejects_truncated_dos_header(self):
        proc = self.run_bytes(b"MZ")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("missing DOS header", proc.stderr)

    def test_rejects_out_of_range_pe_header(self):
        data = bytearray(0x40)
        data[0:2] = b"MZ"
        struct.pack_into("<I", data, 0x3C, 0x1000)
        proc = self.run_bytes(bytes(data))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("missing PE header", proc.stderr)

    def test_canonical_release_engine_invokes_memory_gate(self):
        release_makefile = (ROOT / "xbox" / "release" / "Makefile").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'tools/xbox/verify_xbox_pe_memory.py" "$(CLASSIC_DIR)/main.exe"',
            release_makefile,
        )


if __name__ == "__main__":
    unittest.main()
