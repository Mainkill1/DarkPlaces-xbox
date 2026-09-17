from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "xbox" / "release"


class XboxReleaseMakefileTests(unittest.TestCase):
    def test_help_parses_without_external_dependencies(self):
        proc = subprocess.run(
            ["make", "-C", str(RELEASE), "help"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("bootstrap", proc.stdout)
        self.assertIn("preflight", proc.stdout)
        self.assertIn("stage", proc.stdout)
        self.assertIn("engine", proc.stdout)
        self.assertIn("package", proc.stdout)

    def test_release_wrapper_keeps_network_phases_explicit(self):
        text = (RELEASE / "Makefile").read_text(encoding="utf-8")
        self.assertIn("bootstrap: deps content preflight", text)
        self.assertIn("deps:", text)
        self.assertIn("content:", text)
        self.assertIn("preflight:", text)
        self.assertIn("stage: preflight", text)
        self.assertIn("engine: preflight", text)
        self.assertIn("package: preflight stage identity engine", text)
        self.assertIn("all: preflight stage engine package", text)

    def test_generated_release_outputs_are_named_explicitly(self):
        text = (RELEASE / "Makefile").read_text(encoding="utf-8")
        for name in (
            "nexuiz-xbox.xbe",
            "nexuiz-xbox.iso",
            "BUILD-IDENTITY.txt",
            "CONTENT-IDENTITY.json",
            "SHA256SUMS",
        ):
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
