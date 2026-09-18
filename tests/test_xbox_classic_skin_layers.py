"""Validate the reproducible Xbox material-layer adaptation."""

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deps" / "darkplaces-classic" / "gl_rmain.c"
PATCHER = ROOT / "tools" / "xbox" / "patch_classic_skin_layers.py"


class ClassicSkinLayerPatchTests(unittest.TestCase):
    def test_xbox_profile_controls_optional_material_layer_loading(self):
        original = SOURCE.read_bytes()
        self.assertEqual(
            hashlib.sha256(original).hexdigest(),
            "cdad3b087df8680048c679a0b15f4ece3730d1689cfcf3959ee81b0bdddab542",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "gl_rmain.c"
            proc = subprocess.run(
                [sys.executable, str(PATCHER), str(SOURCE), str(output)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            patched = output.read_text(encoding="utf-8")

        self.assertIn('#include "xbox_memory_profile.h"', patched)
        self.assertIn("extern cvar_t r_shadow_usenormalmap;", patched)
        self.assertRegex(
            patched,
            r"Xbox_MemoryProfileAllowsEnhancedMaterialLayers\(\)\s*&&\s*"
            r"r_shadow_usenormalmap\.integer",
        )
        self.assertRegex(
            patched,
            r"Xbox_MemoryProfileAllowsEnhancedMaterialLayers\(\)\s*&&\s*"
            r"r_shadow_gloss\.integer",
        )
        self.assertEqual(SOURCE.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
