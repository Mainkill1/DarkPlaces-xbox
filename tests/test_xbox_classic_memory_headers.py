"""Verify the classic Xbox build's compile-time memory profile."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "deps" / "darkplaces-classic"
PATCHER = ROOT / "tools" / "xbox" / "patch_classic_memory_headers.py"
CLASSIC = ROOT / "xbox" / "classic"


class ClassicMemoryHeaderTests(unittest.TestCase):
    def test_make_forces_profile_into_engine_and_platform_translation_units(self):
        proc = subprocess.run(
            [
                "make",
                "-C",
                str(CLASSIC),
                "-n",
                "-B",
                "main.exe",
                f"NXDK_DIR={ROOT / 'deps' / 'nxdk'}",
                f"ENGINE_DIR={ENGINE}",
                f"PBGL_DIR={ROOT / 'deps' / 'pbgl'}",
                f"OGG_DIR={ROOT / 'deps' / 'ogg'}",
                f"VORBIS_DIR={ROOT / 'deps' / 'vorbis'}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        compile_lines = {
            source: next(
                (line for line in proc.stdout.splitlines() if line.endswith(f"'{source}'")),
                "",
            )
            for source in (str(ENGINE / "cl_main.c"), str(CLASSIC / "vid_xbox.c"))
        }
        forced_header = f"-include {CLASSIC / 'build/generated/memory/quakedef_xbox.h'}"
        for source, command in compile_lines.items():
            self.assertTrue(command, f"missing dry-run compile command for {source}")
            self.assertIn(forced_header, command)

    def test_generated_headers_apply_stock_memory_limits_to_the_compiler(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(PATCHER),
                    str(ENGINE / "quakedef.h"),
                    str(ENGINE / "netconn.h"),
                    str(output),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

            probe = output / "limits.c"
            probe.write_text(
                """
#include "quakedef_xbox.h"
#include "netconn_xbox.h"
#if MAX_EDICTS != 8192
#error MAX_EDICTS must fit the stock-memory profile
#endif
#if MAX_MODELS != 2048
#error MAX_MODELS must fit the stock-memory profile
#endif
#if MAX_SOUNDS != 2048
#error MAX_SOUNDS must fit the stock-memory profile
#endif
#if SERVERLIST_TOTALSIZE != 256
#error SERVERLIST_TOTALSIZE must fit the stock-memory profile
#endif
""",
                encoding="utf-8",
            )
            compiled = subprocess.run(
                [
                    "cc",
                    "-E",
                    "-I",
                    str(output),
                    "-I",
                    str(ENGINE),
                    str(probe),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)


if __name__ == "__main__":
    unittest.main()
