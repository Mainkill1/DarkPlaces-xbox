"""Compile the real GL compatibility unit against typed adapter contracts."""

from pathlib import Path
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = r'''
#include <GL/gl.h>
static void Xbox_glDrawBuffer(GLenum mode);
static void Xbox_glReadBuffer(GLenum mode);
static void Xbox_glGetDoublev(GLenum pname, GLdouble *params);
static void Xbox_glPixelStoref(GLenum pname, GLfloat value);
static void Xbox_glTexParameterfv(GLenum target, GLenum pname, GLfloat *params);
static void Xbox_glArrayElement(GLint index);
static void Xbox_glTexCoord1f(GLfloat s);
static void Xbox_glMultiTexCoord1f(GLenum unit, GLfloat s);
static void Xbox_glTexImage1D(GLenum target, GLint level, GLint internalformat,
    GLsizei width, GLint border, GLenum format, GLenum type, const GLvoid *pixels);
static void Xbox_glTexSubImage1D(GLenum target, GLint level, GLint xoffset,
    GLsizei width, GLenum format, GLenum type, const GLvoid *pixels);
static void Xbox_glCopyTexImage1D(GLenum target, GLint level, GLenum internalformat,
    GLint x, GLint y, GLsizei width, GLint border);
static void Xbox_glCopyTexSubImage1D(GLenum target, GLint level, GLint xoffset,
    GLint x, GLint y, GLsizei width);
static void Xbox_glPolygonStipple(const GLubyte *mask);
static void Xbox_glClipPlane(GLenum plane, const GLdouble *equation);
static void Xbox_glGetClipPlane(GLenum plane, GLdouble *equation);
'''


class ClassicGlAdapterTypeTests(unittest.TestCase):
    def test_manual_adapters_match_engine_gl_function_types(self):
        compiler = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(compiler and shutil.which(compiler[0]), "A host C compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            contract = Path(directory) / "adapter_contract.h"
            contract.write_text(CONTRACT, encoding="utf-8")
            proc = subprocess.run(
                [
                    *compiler,
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-fsyntax-only",
                    "-include",
                    str(contract),
                    "-I",
                    str(ROOT / "deps" / "darkplaces-classic"),
                    "-I",
                    str(ROOT / "deps" / "pbgl" / "include"),
                    "-I",
                    str(ROOT / "xbox" / "classic" / "include"),
                    "-I",
                    str(ROOT),
                    str(ROOT / "xbox" / "classic" / "gl_compat.c"),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
