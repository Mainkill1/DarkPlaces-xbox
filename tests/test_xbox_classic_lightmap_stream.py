"""Validate bounded external-lightmap ownership in the classic Xbox source."""

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deps" / "darkplaces-classic" / "model_brush.c"
PATCHER = ROOT / "tools" / "xbox" / "patch_classic_lightmaps.py"
MAKEFILE = ROOT / "xbox" / "classic" / "Makefile"


class ClassicLightmapStreamTests(unittest.TestCase):
    def _materialized_source(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "model_brush.c"
            proc = subprocess.run(
                [sys.executable, str(PATCHER), str(SOURCE), str(output)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            return output.read_text(encoding="utf-8")

    def test_external_lightmaps_are_scanned_and_uploaded_with_one_owned_image(self):
        original = SOURCE.read_bytes()
        self.assertEqual(
            hashlib.sha256(original).hexdigest(),
            "e79ca0cf9b8f6abe179b0aef6d06ab94cfaf4a1107c61c16a14ea6a064d508bc",
        )
        patched = self._materialized_source()

        scan = patched.index("Xbox: count and validate external lightmaps one at a time")
        allocate = patched.index("convertedpixels = (unsigned char *) Mem_Alloc", scan)
        upload = patched.index("Xbox: decode each external lightmap only for its upload", allocate)
        self.assertLess(scan, allocate)
        self.assertLess(allocate, upload)
        self.assertIn("Mem_Free(externalpixels);", patched[scan:allocate])
        self.assertIn("externalpixels = loadimagepixelsbgra", patched[upload:])
        self.assertIn("Mem_Free(externalpixels);", patched[upload:])
        self.assertIn("Xbox external lightmaps counted: %i at %ix%i", patched)
        self.assertIn("Xbox external lightmap streaming complete", patched)
        self.assertNotIn("inpixels[count] = loadimagepixelsbgra", patched)
        self.assertEqual(SOURCE.read_bytes(), original)

    def test_patch_tessellation_scratch_is_sized_to_patch_faces(self):
        patched = self._materialized_source()

        self.assertIn("patchtesscapacity = 0;", patched)
        self.assertIn("++patchtesscapacity;", patched)
        self.assertIn("patchtesscapacity * sizeof(*patchtess)", patched)
        self.assertIn("patchtesscount >= patchtesscapacity", patched)
        self.assertIn("Xbox patch tessellation scratch: %i of %i faces", patched)
        self.assertNotIn("count * sizeof(*patchtess)", patched)

    def test_q3_portal_reconstruction_uses_pvs_frustum_fallback(self):
        patched = self._materialized_source()

        q1_loader = patched[patched.index("void Mod_Q1BSP_Load("):]
        q1_loader = q1_loader[:q1_loader.index("void static Mod_Q2BSP_Load(")]
        q3_loader = patched[patched.index("void Mod_Q3BSP_Load("):]
        self.assertIn("Mod_Q1BSP_MakePortals();", q1_loader)
        self.assertNotIn("Mod_Q1BSP_MakePortals();", q3_loader)
        self.assertIn("loadmodel->brush.data_portals = NULL;", q3_loader)
        self.assertIn("loadmodel->brush.num_portals = 0;", q3_loader)
        self.assertIn("loadmodel->brush.data_portalpoints = NULL;", q3_loader)
        self.assertIn("loadmodel->brush.num_portalpoints = 0;", q3_loader)
        self.assertIn("Xbox Q3 portals disabled; using BSP PVS/frustum fallback", q3_loader)

    def test_classic_build_uses_only_the_materialized_model_brush(self):
        text = MAKEFILE.read_text(encoding="utf-8")
        self.assertIn("PATCHED_MODEL_BRUSH :=", text)
        self.assertIn("$(PATCHED_MODEL_BRUSH)", text)
        common = text[text.index("ENGINE_COMMON :="):text.index("ENGINE_SOUND :=")]
        self.assertNotIn("model_brush.c", common)


if __name__ == "__main__":
    unittest.main()
