"""Compile and execute the Xbox stat/mkdir compatibility backend."""

from pathlib import Path
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WINBASE = r'''
#ifndef TEST_WINBASE_H
#define TEST_WINBASE_H
#define MAX_PATH 260
#define FILE_ATTRIBUTE_DIRECTORY 0x10
typedef unsigned long DWORD;
typedef int BOOL;
typedef enum { GetFileExInfoStandard } GET_FILEEX_INFO_LEVELS;
typedef struct {
    DWORD dwFileAttributes;
    DWORD nFileSizeHigh;
    DWORD nFileSizeLow;
} WIN32_FILE_ATTRIBUTE_DATA;
#endif
'''
FILEAPI = r'''
#ifndef TEST_FILEAPI_H
#define TEST_FILEAPI_H
#include <winbase.h>
BOOL GetFileAttributesExA(const char *, GET_FILEEX_INFO_LEVELS, void *);
BOOL CreateDirectoryA(const char *, void *);
#define GetFileAttributesEx GetFileAttributesExA
#define CreateDirectory CreateDirectoryA
#endif
'''
HARNESS = r'''
#include <assert.h>
#include <string.h>
#include <sys/stat.h>
#include <fileapi.h>

BOOL GetFileAttributesExA(const char *path, GET_FILEEX_INFO_LEVELS level, void *output)
{
    WIN32_FILE_ATTRIBUTE_DATA *data = output;
    assert(strcmp(path, "E:\\UDATA\\Nexuiz") == 0);
    assert(level == GetFileExInfoStandard);
    data->dwFileAttributes = FILE_ATTRIBUTE_DIRECTORY;
    data->nFileSizeHigh = 0;
    data->nFileSizeLow = 4096;
    return 1;
}

BOOL CreateDirectoryA(const char *path, void *security)
{
    assert(strcmp(path, "E:\\UDATA\\Nexuiz") == 0);
    assert(security == 0);
    return 1;
}

int main(void)
{
    struct stat information;
    assert(stat("E:/UDATA/Nexuiz", &information) == 0);
    assert(S_ISDIR(information.st_mode));
    assert(information.st_size == 4096);
    assert(mkdir("E:/UDATA/Nexuiz", 0777) == 0);
    return 0;
}
'''


class ClassicStatTests(unittest.TestCase):
    def test_stat_backend_normalizes_paths_and_reports_directories(self):
        compiler = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(compiler and shutil.which(compiler[0]), "A host C compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            (temp / "winbase.h").write_text(WINBASE, encoding="utf-8")
            (temp / "fileapi.h").write_text(FILEAPI, encoding="utf-8")
            harness = temp / "harness.c"
            executable = temp / "stat-test"
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
                    str(ROOT / "xbox" / "classic" / "path_xbox.c"),
                    str(ROOT / "xbox" / "classic" / "stat_xbox.c"),
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
