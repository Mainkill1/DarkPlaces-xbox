"""Exercise classic Xbox memory-profile selection and runtime ceilings."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLASSIC = ROOT / "xbox" / "classic"


class XboxClassicMemoryProfileTests(unittest.TestCase):
    def test_policy_selects_capacity_profiles_and_clamps_only_retail_values(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "memory-policy-test"
            compiled = subprocess.run(
                [
                    "cc",
                    "-std=c99",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(CLASSIC / "include"),
                    str(ROOT / "tests" / "xbox_memory_policy_harness.c"),
                    str(CLASSIC / "memory_policy_xbox.c"),
                    "-o",
                    str(executable),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            run = subprocess.run(
                [str(executable)], capture_output=True, text=True, timeout=30
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_xbox_adapter_queries_memory_parses_override_and_applies_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "memory-profile-test"
            compiled = subprocess.run(
                [
                    "cc",
                    "-std=c99",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(ROOT / "tests" / "classic_memory_profile_stubs"),
                    "-I",
                    str(CLASSIC / "include"),
                    str(ROOT / "tests" / "xbox_memory_profile_harness.c"),
                    str(CLASSIC / "memory_policy_xbox.c"),
                    str(CLASSIC / "memory_profile_xbox.c"),
                    "-o",
                    str(executable),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            run = subprocess.run(
                [str(executable), directory],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
