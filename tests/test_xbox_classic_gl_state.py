"""Exercise Xbox state queries that the pinned pbGL does not implement."""

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
#include <GL/gl.h>
#include <xbox_gl_state.h>

static GLenum active_unit;
static GLenum bound_target;
static GLuint bound_texture;
static unsigned int integer_queries;
static unsigned int boolean_queries;
static unsigned int enabled_queries;

static void CaptureActiveTexture(GLenum unit)
{
    active_unit = unit;
}

static void CaptureBindTexture(GLenum target, GLuint texture)
{
    bound_target = target;
    bound_texture = texture;
}

static void CaptureGetIntegerv(GLenum pname, GLint *value)
{
    ++integer_queries;
    *value = (GLint)pname;
}

static void CaptureGetBooleanv(GLenum pname, GLboolean *value)
{
    ++boolean_queries;
    *value = pname == GL_VERTEX_ARRAY || pname == GL_TEXTURE_COORD_ARRAY;
}

static GLboolean CaptureIsEnabled(GLenum pname)
{
    ++enabled_queries;
    return pname == GL_DEPTH_TEST;
}

int main(void)
{
    GLint value = -1;

    Xbox_GLStateReset();
    Xbox_GLActiveTexture(CaptureActiveTexture, GL_TEXTURE0 + 1);
    assert(active_unit == GL_TEXTURE0 + 1);
    Xbox_GLBindTexture(CaptureBindTexture, GL_TEXTURE_2D, 42);
    assert(bound_target == GL_TEXTURE_2D && bound_texture == 42);
    Xbox_GLGetIntegerv(CaptureGetIntegerv, GL_TEXTURE_BINDING_2D, &value);
    assert(value == 42 && integer_queries == 0);

    Xbox_GLActiveTexture(CaptureActiveTexture, GL_TEXTURE0);
    Xbox_GLGetIntegerv(CaptureGetIntegerv, GL_TEXTURE_BINDING_2D, &value);
    assert(value == 0 && integer_queries == 0);
    Xbox_GLGetIntegerv(CaptureGetIntegerv, GL_MAX_TEXTURE_SIZE, &value);
    assert(value == GL_MAX_TEXTURE_SIZE && integer_queries == 1);

    assert(Xbox_GLIsEnabled(CaptureIsEnabled, CaptureGetBooleanv,
        GL_VERTEX_ARRAY));
    assert(Xbox_GLIsEnabled(CaptureIsEnabled, CaptureGetBooleanv,
        GL_TEXTURE_COORD_ARRAY));
    assert(boolean_queries == 2 && enabled_queries == 0);
    assert(Xbox_GLIsEnabled(CaptureIsEnabled, CaptureGetBooleanv,
        GL_DEPTH_TEST));
    assert(boolean_queries == 2 && enabled_queries == 1);
    return 0;
}
'''


class ClassicGlStateTests(unittest.TestCase):
    def test_missing_pbgl_state_queries_are_supplied_by_adapter(self):
        compiler = shlex.split(os.environ.get("CC", "cc"))
        self.assertTrue(compiler and shutil.which(compiler[0]))
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            harness = temp / "harness.c"
            executable = temp / "gl-state-test"
            harness.write_text(HARNESS, encoding="utf-8")
            build = subprocess.run(
                [
                    *compiler,
                    "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-I", str(ROOT / "deps" / "pbgl" / "include"),
                    "-I", str(ROOT / "xbox" / "classic" / "include"),
                    str(ROOT / "xbox" / "classic" / "gl_state_xbox.c"),
                    str(harness), "-o", str(executable),
                ],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run(
                [str(executable)], capture_output=True, text=True, timeout=5
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
