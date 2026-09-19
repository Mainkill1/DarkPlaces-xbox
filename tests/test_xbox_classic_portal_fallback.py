"""Validate the Xbox Q3 portal-less renderer fallback."""

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deps" / "darkplaces-classic" / "gl_rsurf.c"
PATCHER = ROOT / "tools" / "xbox" / "patch_classic_portal_fallback.py"
MAKEFILE = ROOT / "xbox" / "classic" / "Makefile"


class ClassicPortalFallbackTests(unittest.TestCase):
    def test_portal_less_models_do_not_enter_portal_dependent_svbsp(self):
        original = SOURCE.read_bytes()
        self.assertEqual(
            hashlib.sha256(original).hexdigest(),
            "bc60fe1585765fb18a27636706fa55471c1d972eef0a6655cdf125c84b1bfbf9",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "gl_rsurf.c"
            proc = subprocess.run(
                [sys.executable, str(PATCHER), str(SOURCE), str(output)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            patched = output.read_text(encoding="utf-8")

        self.assertIn(
            "info.model->brush.data_portals &&\n"
            "\t\t\t(r_shadow_compilingrtlight",
            patched,
        )
        self.assertEqual(SOURCE.read_bytes(), original)

    def test_classic_build_uses_materialized_surface_renderer(self):
        text = MAKEFILE.read_text(encoding="utf-8")
        self.assertIn("PATCHED_GL_RSURF :=", text)
        self.assertIn("$(PATCHED_GL_RSURF)", text)
        common = text[text.index("ENGINE_COMMON :="):text.index("ENGINE_SOUND :=")]
        self.assertNotIn("gl_rsurf.c", common)


if __name__ == "__main__":
    unittest.main()
