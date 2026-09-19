#!/usr/bin/env python3
"""Materialize the portal-less Xbox light-culling fallback in gl_rsurf.c."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile


EXPECTED_SHA256 = "bc60fe1585765fb18a27636706fa55471c1d972eef0a6655cdf125c84b1bfbf9"

SVBSP_OLD = '''\
		R_Q1BSP_CallRecursiveGetLightInfo(&info, (r_shadow_compilingrtlight ? r_shadow_realtime_world_compilesvbsp.integer : r_shadow_realtime_dlight_svbspculling.integer) != 0);
'''

SVBSP_NEW = '''\
		R_Q1BSP_CallRecursiveGetLightInfo(&info, info.model->brush.data_portals &&
			(r_shadow_compilingrtlight ? r_shadow_realtime_world_compilesvbsp.integer : r_shadow_realtime_dlight_svbspculling.integer) != 0);
'''


def materialize(source: Path, output: Path) -> None:
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"unexpected pinned gl_rsurf.c identity: {digest}")
    text = data.decode("utf-8")
    if text.count(SVBSP_OLD) != 1:
        raise SystemExit("pinned gl_rsurf.c SVBSP fallback did not match exactly once")
    patched = text.replace(SVBSP_OLD, SVBSP_NEW)
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
