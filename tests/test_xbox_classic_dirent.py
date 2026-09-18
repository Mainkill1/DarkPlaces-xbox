"""Compile and execute the Xbox directory-enumeration compatibility backend."""

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
typedef int BOOL;
typedef void *HANDLE;
typedef struct { char cFileName[MAX_PATH]; } WIN32_FIND_DATAA;
#define INVALID_HANDLE_VALUE ((HANDLE)-1)
#endif
'''
FILEAPI = r'''
#ifndef TEST_FILEAPI_H
#define TEST_FILEAPI_H
#include <winbase.h>
HANDLE FindFirstFileA(const char *, WIN32_FIND_DATAA *);
BOOL FindNextFileA(HANDLE, WIN32_FIND_DATAA *);
BOOL FindClose(HANDLE);
#define FindFirstFile FindFirstFileA
#define FindNextFile FindNextFileA
#endif
'''
HARNESS = r'''
#include <assert.h>
#include <dirent.h>
#include <string.h>
#include <fileapi.h>

static int next_index;

HANDLE FindFirstFileA(const char *pattern, WIN32_FIND_DATAA *data)
{
    assert(strcmp(pattern, "D:\\data\\*") == 0);
    strcpy(data->cFileName, "alpha.pk3");
    next_index = 1;
    return (HANDLE)1;
}

BOOL FindNextFileA(HANDLE handle, WIN32_FIND_DATAA *data)
{
    assert(handle == (HANDLE)1);
    if (next_index++ == 1) {
        strcpy(data->cFileName, "beta.cfg");
        return 1;
    }
    return 0;
}

BOOL FindClose(HANDLE handle)
{
    return handle == (HANDLE)1;
}

int main(void)
{
    /* DarkPlaces' POSIX listdirectory path appends "./" when listing a
     * directory root.  nxdk does not canonicalize that component for us. */
    DIR *directory = opendir("D:/data/./");
    struct dirent *entry;
    assert(directory != 0);
    entry = readdir(directory);
    assert(entry && strcmp(entry->d_name, "alpha.pk3") == 0);
    entry = readdir(directory);
    assert(entry && strcmp(entry->d_name, "beta.cfg") == 0);
    assert(readdir(directory) == 0);
    assert(closedir(directory) == 0);
    return 0;
}
'''


class ClassicDirentTests(unittest.TestCase):
    def test_directory_backend_canonicalizes_engine_probe_and_iterates_entries(self):
        compiler = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(compiler and shutil.which(compiler[0]), "A host C compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            (temp / "winbase.h").write_text(WINBASE, encoding="utf-8")
            (temp / "fileapi.h").write_text(FILEAPI, encoding="utf-8")
            harness = temp / "harness.c"
            executable = temp / "dirent-test"
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
                    str(ROOT / "xbox" / "classic" / "dirent_xbox.c"),
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
