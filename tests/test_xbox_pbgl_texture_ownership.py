"""Pinned pbGL texture-table ownership contract for the classic Xbox build."""

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deps" / "pbgl" / "src" / "texture.c"
PATCHER = ROOT / "tools" / "xbox" / "patch_pbgl_texture.py"
MAKEFILE = ROOT / "xbox" / "classic" / "Makefile"


class PbglTextureOwnershipTests(unittest.TestCase):
    def test_generated_table_rebases_bindings_and_counts_live_ids(self):
        original = SOURCE.read_bytes()
        self.assertEqual(
            hashlib.sha256(original).hexdigest(),
            "4ab9380123d94495a5f6b34e8346f34c131e63ccaab9c8b2508e3078352d4bde",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "texture_xbox.c"
            result = subprocess.run(
                [sys.executable, str(PATCHER), str(SOURCE), str(output)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            patched = output.read_text(encoding="utf-8")

        self.assertIn("(GLuint)(pbgl.tex[unit].tex - textures) : UINT_MAX", patched)
        self.assertIn("pbgl.tex[unit].tex = textures + bound_ids[unit]", patched)
        self.assertIn("if (!textures[id].used)", patched)
        self.assertIn("--tex_count;", patched)
        self.assertIn("for (GLuint i = 0; i < tex_cap; ++i)", patched)
        self.assertNotIn("tex_count -= num;", patched)
        self.assertEqual(SOURCE.read_bytes(), original)

    def test_build_uses_only_generated_texture_translation_unit(self):
        makefile = MAKEFILE.read_text(encoding="utf-8")
        config = (ROOT / "xbox" / "classic" / "pbgl_xbox.make").read_text(encoding="utf-8")
        self.assertIn("include $(CLASSIC_PORT_DIR)/pbgl_xbox.make", makefile)
        self.assertNotIn("include $(PBGL_DIR)/config_pbgl.make", makefile)
        self.assertIn("$(PATCHED_PBGL_TEXTURE)", config)
        self.assertIn("filter-out $(PBGL_DIR)/src/texture.c", config)


if __name__ == "__main__":
    unittest.main()
