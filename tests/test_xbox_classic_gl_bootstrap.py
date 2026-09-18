"""Compile and exercise the classic Xbox GL bootstrap boundary."""

from pathlib import Path
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
GL_H = r'''
#ifndef TEST_GL_H
#define TEST_GL_H
typedef unsigned int GLenum;
typedef unsigned char GLubyte;
#define GLAPIENTRY
#define GL_VENDOR 0x1F00
#define GL_RENDERER 0x1F01
#define GL_VERSION 0x1F02
#define GL_EXTENSIONS 0x1F03
#endif
'''
HARNESS = r'''
#include <assert.h>
#include <stdarg.h>
#include <stddef.h>
#include <string.h>
#include <GL/gl.h>
#include <xbox_gl_bootstrap.h>

const GLubyte* (GLAPIENTRY *qglGetString)(GLenum name);
static int resolver_enabled;
static int string_enabled;
static int query_count;

static const GLubyte *TestGetString(GLenum name)
{
    ++query_count;
    if (!string_enabled)
        return NULL;
    switch (name)
    {
    case GL_VENDOR: return (const GLubyte *)"vendor";
    case GL_RENDERER: return (const GLubyte *)"renderer";
    case GL_VERSION: return (const GLubyte *)"version";
    case GL_EXTENSIONS: return (const GLubyte *)"extensions";
    default: return NULL;
    }
}

void *GL_GetProcAddress(const char *name)
{
    assert(strcmp(name, "glGetString") == 0);
    return resolver_enabled ? (void *)TestGetString : NULL;
}

void Xbox_BootTraceMark(const char *format, ...)
{
    (void)format;
}

int main(void)
{
    assert(Xbox_GLBootstrap(-1) == XBOX_GL_BOOTSTRAP_PBGL_FAILED);
    assert(qglGetString == NULL);

    assert(Xbox_GLBootstrap(0) == XBOX_GL_BOOTSTRAP_RESOLVE_FAILED);
    assert(qglGetString == NULL);

    resolver_enabled = 1;
    assert(Xbox_GLBootstrap(0) == XBOX_GL_BOOTSTRAP_IDENTITY_FAILED);
    assert(qglGetString == TestGetString);

    string_enabled = 1;
    query_count = 0;
    assert(Xbox_GLBootstrap(0) == XBOX_GL_BOOTSTRAP_OK);
    assert(qglGetString == TestGetString);
    assert(query_count == 4);
    return 0;
}
'''


class ClassicGlBootstrapTests(unittest.TestCase):
    def test_pbgl_and_first_gl_dispatch_are_validated_before_engine_gl_init(self):
        compiler = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(compiler and shutil.which(compiler[0]), "A host C compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            (temp / "GL").mkdir()
            (temp / "GL" / "gl.h").write_text(GL_H, encoding="utf-8")
            harness = temp / "harness.c"
            executable = temp / "gl-bootstrap-test"
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
                    str(ROOT / "deps" / "darkplaces-classic"),
                    "-I",
                    str(ROOT / "xbox" / "classic" / "include"),
                    str(ROOT / "xbox" / "classic" / "gl_bootstrap_xbox.c"),
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
