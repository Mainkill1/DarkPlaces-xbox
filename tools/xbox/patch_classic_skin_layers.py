#!/usr/bin/env python3
"""Materialize the Xbox-only classic material-layer memory policy."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile


EXPECTED_SHA256 = "cdad3b087df8680048c679a0b15f4ece3730d1689cfcf3959ee81b0bdddab542"

INCLUDE_OLD = '#include "image.h"\n'
INCLUDE_NEW = '''\
#include "image.h"
#include "xbox_memory_profile.h"

extern cvar_t r_shadow_usenormalmap;
'''

LAYERS_OLD = '''\
\tqboolean loadnormalmap = true;
\tqboolean loadgloss = true;
'''

LAYERS_NEW = '''\
\tqboolean loadnormalmap =
\t\tXbox_MemoryProfileAllowsEnhancedMaterialLayers() &&
\t\tr_shadow_usenormalmap.integer;
\tqboolean loadgloss =
\t\tXbox_MemoryProfileAllowsEnhancedMaterialLayers() &&
\t\tr_shadow_gloss.integer;
'''


def materialize(source: Path, output: Path) -> None:
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"unexpected pinned gl_rmain.c identity: {digest}")
    text = data.decode("utf-8")
    if text.count(INCLUDE_OLD) != 1:
        raise SystemExit("pinned gl_rmain.c image include did not match exactly once")
    if text.count(LAYERS_OLD) != 1:
        raise SystemExit("pinned gl_rmain.c material-layer block did not match exactly once")
    patched = text.replace(INCLUDE_OLD, INCLUDE_NEW).replace(LAYERS_OLD, LAYERS_NEW)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=output.name + ".", dir=output.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as temporary:
            temporary.write(patched)
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
