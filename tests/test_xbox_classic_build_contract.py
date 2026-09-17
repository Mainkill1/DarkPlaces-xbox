from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAKE = ROOT / "xbox" / "classic" / "Makefile"
SYS = ROOT / "xbox" / "classic" / "sys_xbox.c"


class ClassicBuildContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.make = MAKE.read_text(encoding="utf-8")
        cls.sys = SYS.read_text(encoding="utf-8")

    def test_vorbis_build_is_decode_only_and_does_not_wildcard_encoder_sources(self):
        self.assertNotIn("$(wildcard $(VORBIS_DIR)/lib/*.c)", self.make)
        self.assertIn("$(VORBIS_DIR)/lib/vorbisfile.c", self.make)
        self.assertIn("$(VORBIS_DIR)/lib/synthesis.c", self.make)
        self.assertNotIn("$(VORBIS_DIR)/lib/vorbisenc.c", self.make)

    def test_xbox_uses_disc_basedir_and_separate_writable_userdir(self):
        self.assertIn('static char arg3[] = "D:/";', self.sys)
        self.assertIn('static char arg4[] = "-userdir";', self.sys)
        self.assertIn('static char arg5[] = "E:/UDATA/Nexuiz";', self.sys)
        self.assertIn("com_argc = 13;", self.sys)
        self.assertIn("XBOX_USERDIR", self.sys)

    def test_xbox_startup_reports_both_storage_roots(self):
        self.assertIn("basedir=D:/", self.sys)
        self.assertIn("userdir=E:/UDATA/Nexuiz", self.sys)


if __name__ == "__main__":
    unittest.main()
