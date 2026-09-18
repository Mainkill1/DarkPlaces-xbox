"""Compile and execute classic-engine CRT functions missing from nxdk PDCLib."""

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
#include <math.h>
#include <stdlib.h>

static int near(double actual, double expected)
{
    return fabs(actual - expected) < 0.000001;
}

int main(void)
{
    assert(near(atof("0"), 0.0));
    assert(near(atof("  -12.5"), -12.5));
    assert(near(atof("+0.03125"), 0.03125));
    assert(near(atof("1.25e2"), 125.0));
    assert(near(atof("4E-2"), 0.04));
    assert(near(atof("3.5 trailing"), 3.5));
    assert(near(atof("invalid"), 0.0));
    return 0;
}
'''


class ClassicCrtTests(unittest.TestCase):
    def test_atof_parses_engine_configuration_numbers(self):
        compiler = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(compiler and shutil.which(compiler[0]), "A host C compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            harness = temp / "harness.c"
            executable = temp / "crt-test"
            harness.write_text(HARNESS, encoding="utf-8")
            build = subprocess.run(
                [
                    *compiler,
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    str(ROOT / "xbox" / "classic" / "crt_xbox.c"),
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
