from pathlib import Path
import shlex
import subprocess
import tempfile
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
        self.assertIn("VORBIS_CORE_NAMES :=", self.make)
        self.assertIn("synthesis.c", self.make)
        self.assertIn("$(addprefix $(VORBIS_DIR)/lib/,$(VORBIS_CORE_NAMES))", self.make)
        self.assertIn("$(VORBIS_DIR)/lib/vorbisfile.c", self.make)
        self.assertNotIn("$(VORBIS_DIR)/lib/vorbisenc.c", self.make)

    def test_xbox_uses_disc_basedir_and_separate_writable_userdir(self):
        self.assertIn('#define XBOX_BASEDIR "D:/"', self.sys)
        self.assertIn('#define XBOX_USERDIR "E:/UDATA/Nexuiz"', self.sys)
        self.assertIn('static char arg3[] = XBOX_BASEDIR;', self.sys)
        self.assertIn('static char arg4[] = "-userdir";', self.sys)
        self.assertIn('static char arg5[] = XBOX_USERDIR;', self.sys)
        self.assertIn("com_argc = 13;", self.sys)

    def test_xbox_startup_reports_both_storage_roots(self):
        self.assertIn("basedir=D:/", self.sys)
        self.assertIn("userdir=E:/UDATA/Nexuiz", self.sys)

    def test_xbox_compiler_profile_does_not_select_the_msvc_crt(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            nxdk = tmp_path / "nxdk"
            pbgl = tmp_path / "pbgl"
            nxdk.mkdir()
            pbgl.mkdir()
            (nxdk / "Makefile").write_text(
                "%.obj: %.c\n\t@printf '%s\\n' \"$(CFLAGS)\"\n", encoding="utf-8"
            )
            (pbgl / "config_pbgl.make").write_text("", encoding="utf-8")

            proc = subprocess.run(
                [
                    "make",
                    "--no-print-directory",
                    "-B",
                    str(ROOT / "xbox" / "classic" / "posix_io.obj"),
                    f"NXDK_DIR={nxdk}",
                    f"PBGL_DIR={pbgl}",
                ],
                cwd=MAKE.parent,
                check=True,
                capture_output=True,
                text=True,
            )
            profile_flags = [
                flag for flag in shlex.split(proc.stdout) if flag.startswith(("-D", "-U"))
            ]

        probe = """
#ifndef DP_PLATFORM_XBOX
#error Xbox platform identity is missing
#endif
#ifdef _MSC_VER
#error Xbox engine sources must not select the Microsoft CRT
#endif
int main(void) { return 0; }
"""
        proc = subprocess.run(
            ["cc", "-D_MSC_VER=1933", *profile_flags, "-x", "c", "-fsyntax-only", "-"],
            input=probe,
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_xbox_application_flags_do_not_leak_into_nxdk_runtime_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            nxdk = tmp_path / "nxdk"
            pbgl = tmp_path / "pbgl"
            runtime_source = nxdk / "runtime.c"
            nxdk.mkdir()
            pbgl.mkdir()
            runtime_source.write_text("int nxdk_runtime;\n", encoding="utf-8")
            (nxdk / "Makefile").write_text(
                "%.obj: %.c\n\t@printf '%s\\n' \"$(CFLAGS)\"\n", encoding="utf-8"
            )
            (pbgl / "config_pbgl.make").write_text("", encoding="utf-8")
            variables = [f"NXDK_DIR={nxdk}", f"PBGL_DIR={pbgl}"]

            app = subprocess.run(
                [
                    "make",
                    "--no-print-directory",
                    "-B",
                    str(ROOT / "xbox" / "classic" / "posix_io.obj"),
                    *variables,
                ],
                cwd=MAKE.parent,
                check=True,
                capture_output=True,
                text=True,
            )
            runtime = subprocess.run(
                [
                    "make",
                    "--no-print-directory",
                    "-B",
                    str(runtime_source.with_suffix(".obj")),
                    *variables,
                ],
                cwd=MAKE.parent,
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertIn("xbox_posix_io.h", app.stdout)
        self.assertIn("-DDP_PLATFORM_XBOX=1", app.stdout)
        self.assertNotIn("xbox_posix_io.h", runtime.stdout)
        self.assertNotIn("-DDP_PLATFORM_XBOX=1", runtime.stdout)


if __name__ == "__main__":
    unittest.main()
