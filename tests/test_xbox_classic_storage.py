"""Compile and exercise the Xbox writable-storage mount boundary."""

from pathlib import Path
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MOUNT_H = r'''
#ifndef TEST_NXDK_MOUNT_H
#define TEST_NXDK_MOUNT_H
#include <stdbool.h>
bool nxIsDriveMounted(char drive);
bool nxMountDrive(char drive, const char *path);
#endif
'''
HARNESS = r'''
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include <xbox_storage.h>

static bool mounted;
static int mount_calls;

bool nxIsDriveMounted(char drive)
{
    assert(drive == 'E');
    return mounted;
}

bool nxMountDrive(char drive, const char *path)
{
    assert(drive == 'E');
    assert(strcmp(path, "\\Device\\Harddisk0\\Partition1\\") == 0);
    ++mount_calls;
    return true;
}

int main(void)
{
    mounted = true;
    assert(Xbox_MountWritableStorage() == 0);
    assert(mount_calls == 0);
    mounted = false;
    assert(Xbox_MountWritableStorage() == 0);
    assert(mount_calls == 1);
    return 0;
}
'''


class ClassicStorageTests(unittest.TestCase):
    def test_existing_mount_is_preserved_and_missing_e_drive_is_mounted(self):
        compiler = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(compiler and shutil.which(compiler[0]), "A host C compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            nxdk = temp / "nxdk"
            nxdk.mkdir()
            (nxdk / "mount.h").write_text(MOUNT_H, encoding="utf-8")
            harness = temp / "harness.c"
            executable = temp / "storage-test"
            harness.write_text(HARNESS, encoding="utf-8")
            build = subprocess.run(
                [
                    *compiler,
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(temp),
                    "-I",
                    str(ROOT / "xbox" / "classic" / "include"),
                    str(ROOT / "xbox" / "classic" / "storage_xbox.c"),
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
