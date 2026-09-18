"""Behavioral tests for the classic Xbox BGRA upload boundary."""

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
#include <string.h>
#include <GL/gl.h>
#include <GL/glext.h>
#include <xbox_gl_upload.h>

static GLenum seen_target;
static GLint seen_level;
static GLint seen_internal;
static GLint seen_x;
static GLint seen_y;
static GLsizei seen_width;
static GLsizei seen_height;
static GLint seen_border;
static GLenum seen_format;
static GLenum seen_type;
static const GLvoid *seen_pointer;
static unsigned char seen_pixels[32];

static void CaptureImage(GLenum target, GLint level, GLint internalformat,
    GLsizei width, GLsizei height, GLint border, GLenum format, GLenum type,
    const GLvoid *pixels)
{
    seen_target = target;
    seen_level = level;
    seen_internal = internalformat;
    seen_width = width;
    seen_height = height;
    seen_border = border;
    seen_format = format;
    seen_type = type;
    seen_pointer = pixels;
    if (pixels != NULL && width > 0 && height > 0 && width * height * 4 <= 32)
        memcpy(seen_pixels, pixels, (size_t)width * (size_t)height * 4);
}

static void CaptureSubImage(GLenum target, GLint level, GLint xoffset,
    GLint yoffset, GLsizei width, GLsizei height, GLenum format, GLenum type,
    const GLvoid *pixels)
{
    seen_x = xoffset;
    seen_y = yoffset;
    CaptureImage(target, level, 0, width, height, 0, format, type, pixels);
}

int main(void)
{
    static const unsigned char bgra[] = {
        1, 2, 3, 4, 10, 20, 30, 40,
        50, 60, 70, 80, 90, 100, 110, 120
    };
    static const unsigned char rgba[] = {
        3, 2, 1, 4, 30, 20, 10, 40,
        70, 60, 50, 80, 110, 100, 90, 120
    };
    unsigned char original[sizeof(bgra)];
    memcpy(original, bgra, sizeof(bgra));

    Xbox_GLTexImage2D(CaptureImage, GL_TEXTURE_2D, 3, GL_RGBA8,
        2, 2, 0, GL_BGRA, GL_UNSIGNED_BYTE, bgra);
    assert(seen_target == GL_TEXTURE_2D && seen_level == 3);
    assert(seen_internal == GL_RGBA8 && seen_width == 2 && seen_height == 2);
    assert(seen_border == 0 && seen_format == GL_RGBA && seen_type == GL_UNSIGNED_BYTE);
    assert(memcmp(seen_pixels, rgba, sizeof(rgba)) == 0);
    assert(memcmp(bgra, original, sizeof(bgra)) == 0);
    assert(seen_pointer != bgra);

    Xbox_GLTexSubImage2D(CaptureSubImage, GL_TEXTURE_2D, 2, 7, 9,
        2, 2, GL_BGRA, GL_UNSIGNED_BYTE, bgra);
    assert(seen_level == 2 && seen_x == 7 && seen_y == 9);
    assert(seen_format == GL_RGBA);
    assert(memcmp(seen_pixels, rgba, sizeof(rgba)) == 0);

    Xbox_GLTexImage2D(CaptureImage, GL_TEXTURE_2D, 0, GL_RGBA,
        4, 4, 0, GL_BGRA, GL_UNSIGNED_BYTE, NULL);
    assert(seen_format == GL_RGBA && seen_pointer == NULL);

    Xbox_GLTexImage2D(CaptureImage, GL_TEXTURE_2D, 0, GL_RGBA,
        2, 2, 0, GL_RGBA, GL_UNSIGNED_BYTE, bgra);
    assert(seen_format == GL_RGBA && seen_pointer == bgra);

    Xbox_GLTexImage2D(CaptureImage, GL_TEXTURE_2D, 0, GL_RGBA,
        2, 2, 0, GL_BGRA, GL_UNSIGNED_SHORT_4_4_4_4, bgra);
    assert(seen_format == GL_BGRA && seen_pointer == bgra);

    /* The fixed staging limit fails visibly through pbGL's unsupported BGRA path. */
    Xbox_GLTexImage2D(CaptureImage, GL_TEXTURE_2D, 0, GL_RGBA,
        4096, 4096, 0, GL_BGRA, GL_UNSIGNED_BYTE, bgra);
    assert(seen_format == GL_BGRA && seen_pointer == bgra);
    return 0;
}
'''


class ClassicBgraUploadTests(unittest.TestCase):
    def test_bgra_conversion_preserves_source_and_upload_contract(self):
        compiler = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(compiler and shutil.which(compiler[0]), "A host C compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            harness = temp / "harness.c"
            executable = temp / "bgra-upload-test"
            harness.write_text(HARNESS, encoding="utf-8")
            build = subprocess.run(
                [
                    *compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-I", str(ROOT / "deps" / "pbgl" / "include"),
                    "-I", str(ROOT / "xbox" / "classic" / "include"),
                    str(ROOT / "xbox" / "classic" / "gl_upload_xbox.c"),
                    str(harness), "-o", str(executable),
                ], capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run([str(executable)], capture_output=True, text=True, timeout=5)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
