"""Exercise Xbox DOS-path canonicalization used at every nxdk file boundary."""

from pathlib import Path
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HARNESS = r'''
#include <assert.h>
#include <errno.h>
#include <string.h>
#include "xbox_path.h"

static void check(const char *source, const char *expected)
{
    char output[260];
    assert(Xbox_NormalizePath(source, output, sizeof(output)) == 0);
    assert(strcmp(output, expected) == 0);
}

int main(void)
{
    char too_small[4];
    check("D:/data/data20091001.pk3", "D:\\data\\data20091001.pk3");
    check("D:/data/./", "D:\\data\\");
    check("E:/UDATA/Nexuiz/./config.cfg", "E:\\UDATA\\Nexuiz\\config.cfg");
    check("./relative.cfg", "relative.cfg");
    errno = 0;
    assert(Xbox_NormalizePath("D:/data", too_small, sizeof(too_small)) == -1);
    assert(errno == ENAMETOOLONG);
    return 0;
}
'''


class ClassicPathTests(unittest.TestCase):
    def test_path_backend_converts_separators_and_removes_dot_components(self):
        compiler = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(compiler and shutil.which(compiler[0]), "A host C compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            harness = temp / "harness.c"
            executable = temp / "path-test"
            harness.write_text(HARNESS, encoding="utf-8")
            build = subprocess.run(
                [
                    *compiler,
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(ROOT / "xbox" / "classic" / "include"),
                    str(ROOT / "xbox" / "classic" / "path_xbox.c"),
                    str(harness),
                    "-o",
                    str(executable),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(executable)], capture_output=True, text=True, timeout=5)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
