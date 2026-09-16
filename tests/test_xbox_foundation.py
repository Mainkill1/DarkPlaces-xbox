from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_FILES = (
    "xbox/Makefile",
    "xbox/nxdk.version",
    "xbox/config_xbox.h",
    "xbox/port_contract.h",
    "xbox/port_contract.c",
    "xbox/smoke/main.c",
    "tools/xbox/verify_nxdk.py",
    ".github/workflows/xbox-foundation.yml",
)


class XboxFoundationTests(unittest.TestCase):
    def read_required(self, relative_path: str) -> str:
        path = ROOT / relative_path
        self.assertTrue(path.is_file(), f"required foundation file is missing: {relative_path}")
        return path.read_text(encoding="utf-8")

    def load_verifier(self):
        path = ROOT / "tools/xbox/verify_nxdk.py"
        self.assertTrue(path.is_file(), "tools/xbox/verify_nxdk.py is missing")
        spec = importlib.util.spec_from_file_location("verify_nxdk", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_expected_foundation_files_exist(self) -> None:
        missing = [name for name in EXPECTED_FILES if not (ROOT / name).is_file()]
        self.assertEqual([], missing, "missing foundation files: " + ", ".join(missing))

    def test_nxdk_pin_is_a_full_commit_sha(self) -> None:
        pin = self.read_required("xbox/nxdk.version").strip()
        self.assertRegex(pin, re.compile(r"^[0-9a-f]{40}$"))

    def test_makefile_is_a_pinned_non_sdl_nxdk_target(self) -> None:
        makefile = self.read_required("xbox/Makefile")
        required_tokens = (
            "NXDK_DIR ?=",
            "NXDK_PIN_FILE :=",
            "ALLOW_UNPINNED_NXDK",
            "OUTPUT_DIR",
            "GEN_XISO",
            "SRCS",
            "include $(NXDK_DIR)/Makefile",
        )
        for token in required_tokens:
            self.assertIn(token, makefile)
        self.assertNotIn("NXDK_SDL", makefile)
        self.assertIn("smoke/main.c", makefile)
        self.assertIn("port_contract.c", makefile)

    def test_config_declares_the_foundation_profile_and_explicit_caps(self) -> None:
        config = self.read_required("xbox/config_xbox.h")
        required_tokens = (
            "DP_PLATFORM_XBOX",
            "DP_XBOX_BENCHMARK",
            "DP_SMALLMEMORY",
            'DP_XBOX_PROFILE_NAME "foundation"',
            "DP_XBOX_MEMORY_TARGET_MIB 64",
            "DP_XBOX_CAP_RENDERER 0",
            "DP_XBOX_CAP_AUDIO 0",
            "DP_XBOX_CAP_NETWORK 0",
            "DP_XBOX_CAP_DYNAMIC_LOADING 0",
            "DP_XBOX_CAP_FILESYSTEM_WRITE 0",
        )
        for token in required_tokens:
            self.assertIn(token, config)

    def test_smoke_target_is_diagnostic_only_and_has_no_sdl_dependency(self) -> None:
        source = self.read_required("xbox/smoke/main.c")
        for token in (
            "<hal/debug.h>",
            "<hal/video.h>",
            "<windows.h>",
            "XVideoSetMode",
            "debugClearScreen",
            "GetTickCount",
            "Sleep",
            "DP_XboxBootStageName",
            "DP_XboxPortCapabilities",
        ):
            self.assertIn(token, source)
        self.assertNotIn("SDL", source)
        self.assertIn("not the DarkPlaces engine", source)

    def test_nxdk_verifier_rejects_bad_and_mismatched_revisions(self) -> None:
        verifier = self.load_verifier()
        pin = "a" * 40
        other = "b" * 40

        self.assertEqual(pin, verifier.normalize_sha("A" * 40 + "\n"))
        with self.assertRaises(ValueError):
            verifier.normalize_sha("abc123")

        ok, message = verifier.check_revision(pin, pin)
        self.assertTrue(ok)
        self.assertIn("matches", message)

        ok, message = verifier.check_revision(pin, other)
        self.assertFalse(ok)
        self.assertIn(pin, message)
        self.assertIn(other, message)

        ok, message = verifier.check_revision(pin, other, allow_mismatch=True)
        self.assertTrue(ok)
        self.assertIn("override", message.lower())

    def test_port_contract_compiles_and_reports_expected_foundation_state(self) -> None:
        cc = shutil.which("cc")
        if cc is None:
            self.skipTest("host C compiler is unavailable")

        self.read_required("xbox/config_xbox.h")
        self.read_required("xbox/port_contract.h")
        self.read_required("xbox/port_contract.c")

        harness = textwrap.dedent(
            """
            #include <string.h>
            #include "port_contract.h"

            int main(void)
            {
                const dp_xbox_port_capabilities_t *caps = DP_XboxPortCapabilities();
                if (caps == 0)
                    return 1;
                if (caps->memory_target_mib != 64u)
                    return 2;
                if (caps->renderer || caps->audio || caps->network ||
                    caps->dynamic_loading || caps->filesystem_write)
                    return 3;
                if (strcmp(DP_XboxBootStageName(DP_XBOX_BOOT_ENTRY), "entry") != 0)
                    return 4;
                if (strcmp(DP_XboxBootStageName(DP_XBOX_BOOT_STABLE_IDLE), "stable-idle") != 0)
                    return 5;
                if (strcmp(DP_XboxBootStageName((dp_xbox_boot_stage_t)-1), "invalid") != 0)
                    return 6;
                if (strcmp(DP_XboxBootStageName(DP_XBOX_BOOT_STAGE_COUNT), "invalid") != 0)
                    return 7;
                return 0;
            }
            """
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            harness_path = temp / "contract_test.c"
            executable = temp / "contract_test"
            harness_path.write_text(harness, encoding="utf-8")

            compile_result = subprocess.run(
                [
                    cc,
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-pedantic",
                    "-I",
                    str(ROOT / "xbox"),
                    str(ROOT / "xbox/port_contract.c"),
                    str(harness_path),
                    "-o",
                    str(executable),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(0, compile_result.returncode, compile_result.stdout)

            run_result = subprocess.run(
                [str(executable)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(0, run_result.returncode, run_result.stdout)


if __name__ == "__main__":
    unittest.main()
