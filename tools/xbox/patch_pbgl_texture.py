#!/usr/bin/env python3
"""Materialize Xbox texture-table lifetime fixes for the pinned pbGL source."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile


EXPECTED_SHA256 = "4ab9380123d94495a5f6b34e8346f34c131e63ccaab9c8b2508e3078352d4bde"


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"pinned pbGL texture.c pattern did not match once: {old[:80]}")
    return text.replace(old, new)


def materialize(source: Path, output: Path) -> None:
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"unexpected pinned pbGL texture.c identity: {digest}")
    text = data.decode("utf-8")
    text = replace_once(text, "#include <limits.h>\n", "#include <limits.h>\n#include <stdint.h>\n")
    text = replace_once(
        text,
        "  for (GLuint i = 0; i < tex_count; ++i) {\n    if (textures[i].used)",
        "  for (GLuint i = 0; i < tex_cap; ++i) {\n    if (textures[i].used)",
    )
    text = replace_once(
        text,
        "  for (GLuint i = 0; i < tex_count; ++i) {\n    const texture_t *tex = textures + i;",
        "  for (GLuint i = 0; i < tex_cap; ++i) {\n    const texture_t *tex = textures + i;",
    )
    start = text.index("GL_API void glGenTextures(")
    end = text.index("GL_API void glBindTexture(", start)
    text = text[:start] + '''GL_API void glGenTextures(GLsizei num, GLuint *out) {
  if (num < 0 || (num > 0 && !out)) {
    pbgl_set_error(GL_INVALID_VALUE);
    return;
  }
  if (!num) return;

  GLuint free_count = 0;
  for (GLuint id = 1; id < tex_cap; ++id)
    if (!textures[id].used) ++free_count;

  if (free_count < (GLuint)num) {
    const GLuint step = umax(TEX_ALLOC_STEP, (GLuint)num - free_count);
    if (step > UINT_MAX - tex_cap || tex_cap + step > SIZE_MAX / sizeof(texture_t)) {
      pbgl_set_error(GL_OUT_OF_MEMORY);
      return;
    }

    // Bound texture units retain pointers into this table. Capture indices
    // before realloc and rebuild every pointer if the table moves.
    GLuint bound_ids[TEXUNIT_COUNT];
    for (GLuint unit = 0; unit < TEXUNIT_COUNT; ++unit)
      bound_ids[unit] = pbgl.tex[unit].tex
        ? (GLuint)(pbgl.tex[unit].tex - textures) : UINT_MAX;

    const GLuint old_cap = tex_cap;
    texture_t *newtex = realloc(textures, sizeof(texture_t) * (tex_cap + step));
    if (!newtex) {
      pbgl_set_error(GL_OUT_OF_MEMORY);
      return;
    }
    textures = newtex;
    tex_cap += step;
    memset(textures + old_cap, 0, step * sizeof(texture_t));
    for (GLuint unit = 0; unit < TEXUNIT_COUNT; ++unit)
      if (bound_ids[unit] != UINT_MAX)
        pbgl.tex[unit].tex = textures + bound_ids[unit];
  }

  GLuint made = 0;
  for (GLuint id = 1; id < tex_cap && made < (GLuint)num; ++id) {
    if (textures[id].used) continue;
    out[made++] = id;
    textures[id].used = GL_TRUE;
    textures[id].gl = textures[0].gl;
  }
  tex_count += made;
}

GL_API void glDeleteTextures(GLsizei num, const GLuint *ids) {
  if (num < 0 || (num > 0 && !ids)) {
    pbgl_set_error(GL_INVALID_VALUE);
    return;
  }
  for (GLsizei i = 0; i < num; ++i) {
    const GLuint id = ids[i];
    if (!id || id >= tex_cap) continue;
    if (!textures[id].used) continue;
    texture_t *tex = textures + id;
    for (GLuint unit = 0; unit < TEXUNIT_COUNT; ++unit) {
      if (pbgl.tex[unit].tex != tex) continue;
      tex->bound = GL_TRUE; // tex_free must wait for GPU use.
      pbgl.tex[unit].tex = NULL;
      pbgl.tex[unit].enabled = GL_FALSE;
      pbgl.tex[unit].dirty = GL_TRUE;
      pbgl.state_dirty = pbgl.tex_any_dirty = pbgl.texenv_dirty = GL_TRUE;
    }
    tex_free(tex);
    --tex_count;
  }
}

''' + text[end:]
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=output.name + ".", dir=output.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as temporary:
            temporary.write(text)
        os.replace(temporary_name, output)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"usage: {argv[0]} SOURCE OUTPUT", file=sys.stderr)
        return 2
    materialize(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
