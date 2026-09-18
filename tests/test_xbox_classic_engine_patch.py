"""Validate deterministic materialization of the pinned classic engine fix."""

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deps" / "darkplaces-classic" / "fs.c"
PATCHER = ROOT / "tools" / "xbox" / "patch_classic_fs.py"


class ClassicEnginePatchTests(unittest.TestCase):
    def test_inflate_failure_frees_toolkit_and_reports_abi_inputs(self):
        original = SOURCE.read_bytes()
        self.assertEqual(
            hashlib.sha256(original).hexdigest(),
            "433ed0f346ece7a0d8920db4ec7a21ee60215070be01214e144c075cae69791e",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "fs.c"
            proc = subprocess.run(
                [sys.executable, str(PATCHER), str(SOURCE), str(output)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            patched = output.read_text(encoding="utf-8")

        self.assertIn("inflate init error (result: %d", patched)
        self.assertIn("window: %d, stream size: %u", patched)
        free_toolkit = patched.index("Mem_Free(ztk);")
        free_file = patched.index("Mem_Free(file);", free_toolkit)
        self.assertLess(free_toolkit, free_file)
        self.assertEqual(SOURCE.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
