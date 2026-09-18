from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "xbox" / "release"
WRAPPER = RELEASE / "toolchain" / "llvm-dlltool"


class XboxReleaseToolchainTests(unittest.TestCase):
    def test_versioned_llvm_dlltool_is_forwarded(self):
        self.assertTrue(WRAPPER.is_file(), f"missing release tool wrapper: {WRAPPER}")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            tool = temp / "llvm-dlltool-19"
            tool.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\"\n", encoding="utf-8")
            tool.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(temp)
            proc = subprocess.run(
                [str(WRAPPER), "-m", "i386"],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(proc.stdout.splitlines(), ["-m", "i386"])

    def test_release_build_exports_its_host_tool_wrappers(self):
        print_path = 'print-release-path: ; @printf \'%s\\n\' "$(PATH)"'
        proc = subprocess.run(
            [
                "make",
                "--no-print-directory",
                "--eval",
                print_path,
                "print-release-path",
            ],
            cwd=RELEASE,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn(str(WRAPPER.parent), proc.stdout.splitlines()[-1].split(":"))


if __name__ == "__main__":
    unittest.main()
