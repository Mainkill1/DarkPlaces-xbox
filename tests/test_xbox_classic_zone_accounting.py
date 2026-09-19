"""Contract for the Xbox-only classic zone allocator correction."""

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deps" / "darkplaces-classic" / "zone.c"
PATCHER = ROOT / "tools" / "xbox" / "patch_classic_zone.py"
MAKEFILE = ROOT / "xbox" / "classic" / "Makefile"


class ClassicZoneAccountingTests(unittest.TestCase):
    def test_generated_allocator_uses_one_trailer_size_for_alloc_free_and_poison(self):
        original = SOURCE.read_bytes()
        self.assertEqual(
            hashlib.sha256(original).hexdigest(),
            "fa09ff1852c67bcf71c751272c328057828198d2305af7d78f2b3647411accfb",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "zone_xbox.c"
            result = subprocess.run(
                [sys.executable, str(PATCHER), str(SOURCE), str(output)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            patched = output.read_text(encoding="utf-8")

        self.assertIn("#define XBOX_ZONE_TRAILER_BYTES sizeof(unsigned char)", patched)
        self.assertIn("#define XBOX_ZONE_TRAILER_BYTES sizeof(unsigned int)", patched)
        self.assertIn("malloc(sizeof(memheader_t) + size + XBOX_ZONE_TRAILER_BYTES)", patched)
        self.assertIn("pool->realsize -= sizeof(memheader_t) + mem->size + XBOX_ZONE_TRAILER_BYTES", patched)
        self.assertIn("memset(mem, 0xBF, sizeof(memheader_t) + mem->size + XBOX_ZONE_TRAILER_BYTES)", patched)
        self.assertIn("Mem_Alloc: out of memory (%lu bytes in pool %s at %s:%i)", patched)
        self.assertNotIn("pool->realsize -= sizeof(memheader_t) + mem->size + sizeof(int)", patched)
        self.assertEqual(SOURCE.read_bytes(), original)

    def test_classic_build_uses_materialized_zone_only(self):
        makefile = MAKEFILE.read_text(encoding="utf-8")
        self.assertIn("PATCHED_ZONE :=", makefile)
        self.assertIn("$(PATCHED_ZONE)", makefile)
        common = makefile[makefile.index("ENGINE_COMMON :="):makefile.index("ENGINE_SOUND :=")]
        self.assertNotIn("zone.c", common)


if __name__ == "__main__":
    unittest.main()
