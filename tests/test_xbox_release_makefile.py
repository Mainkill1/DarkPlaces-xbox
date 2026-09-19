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
        self.assertIn("CONTENT_PROFILE=stock64|dev128", proc.stdout)
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
        self.assertIn("package:", text)
        self.assertIn("OUT_DIR := $(CURDIR)/out/$(CONTENT_PROFILE)", text)
        self.assertIn('echo "content_profile=$(CONTENT_PROFILE)"', text)

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

    def test_release_wrapper_owns_fresh_xiso_creation_and_verification(self):
        text = (RELEASE / "Makefile").read_text(encoding="utf-8")
        self.assertIn("verify-tree:", text)
        self.assertIn("xiso:", text)
        self.assertIn("verify-xiso:", text)
        self.assertIn('rm -f "$(XISO)"', text)
        self.assertIn('$(EXTRACT_XISO) -c "$(DISC_DIR)" "$(XISO)"', text)
        self.assertIn("verify_release_tree.py", text)
        self.assertIn("verify_xiso.py", text)
        self.assertIn("set_xbe_memory_profile.py", text)
        self.assertNotIn('$(MAKE) -C "$(CLASSIC_DIR)" V=1 all', text)


if __name__ == "__main__":
    unittest.main()
