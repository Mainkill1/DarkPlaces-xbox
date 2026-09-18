"""Exercise the durable, flush-on-write Xbox boot trace."""

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
#include <stdio.h>
#include <string.h>
#include "xbox_boot_trace.h"

int main(int argc, char **argv)
{
    FILE *reader;
    char contents[256] = {0};
    size_t length;

    assert(argc == 2);
    assert(Xbox_BootTraceOpen(argv[1]) == 0);
    Xbox_BootTraceMark("before video");
    Xbox_BootTraceWrite("console line\n");
    Xbox_BootTraceMark("after video");

    /* The process has not closed the writer: successful reading here proves
     * each diagnostic boundary is durable before a later hang or crash. */
    reader = fopen(argv[1], "rb");
    assert(reader != NULL);
    length = fread(contents, 1, sizeof(contents) - 1, reader);
    fclose(reader);
    contents[length] = '\0';
    assert(strcmp(contents,
        "0001 boot trace opened\n"
        "0002 before video\n"
        "console line\n"
        "0003 after video\n") == 0);
    Xbox_BootTraceClose();
    return 0;
}
'''


class ClassicBootTraceTests(unittest.TestCase):
    def test_each_marker_is_durable_before_trace_close(self):
        compiler = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(compiler and shutil.which(compiler[0]), "A host C compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            harness = temp / "harness.c"
            executable = temp / "boot-trace-test"
            trace = temp / "boot-trace.txt"
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
                    str(ROOT / "xbox" / "classic" / "boot_trace_xbox.c"),
                    str(harness),
                    "-o",
                    str(executable),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run(
                [str(executable), str(trace)], capture_output=True, text=True, timeout=5
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
