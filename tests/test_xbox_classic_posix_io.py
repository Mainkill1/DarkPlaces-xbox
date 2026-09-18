"""Compile and execute the Xbox POSIX file-descriptor compatibility backend."""

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
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    const char payload[] = "nexuiz-xbox";
    char buffer[sizeof(payload)] = {0};
    int fd;
    int copy;

    assert(argc == 2);
    fd = open(argv[1], O_CREAT | O_TRUNC | O_RDWR | O_BINARY, 0666);
    assert(fd >= 0);
    assert(write(fd, payload, sizeof(payload)) == (ssize_t)sizeof(payload));
    assert(lseek(fd, 0, SEEK_SET) == 0);
    assert(read(fd, buffer, sizeof(buffer)) == (ssize_t)sizeof(buffer));
    assert(memcmp(buffer, payload, sizeof(payload)) == 0);

    assert(lseek(fd, 2, SEEK_SET) == 2);
    copy = dup(fd);
    assert(copy >= 0 && copy != fd);
    assert(read(copy, buffer, 1) == 1 && buffer[0] == payload[2]);
    assert(lseek(fd, 0, SEEK_CUR) == 3);
    assert(close(fd) == 0);
    assert(read(copy, buffer, 1) == 1 && buffer[0] == payload[3]);
    assert(close(copy) == 0);

    assert(unlink(argv[1]) == 0);
    return 0;
}
'''


class ClassicPosixIoTests(unittest.TestCase):
    def test_file_descriptor_backend_preserves_shared_dup_position(self):
        compiler = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(compiler and shutil.which(compiler[0]), "A host C compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            harness = temp / "harness.c"
            executable = temp / "posix-io-test"
            # A backslash is an ordinary host filename character.  Passing a
            # forward-slash path therefore proves the Xbox adapter converts it
            # before both fopen and remove are reached.
            data = temp / "subdir\\data.pk3"
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
                    str(ROOT / "xbox" / "classic" / "posix_io.c"),
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
                [str(executable), "subdir/data.pk3"],
                cwd=temp,
                capture_output=True,
                text=True,
                timeout=5,
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertFalse(data.exists())


if __name__ == "__main__":
    unittest.main()
