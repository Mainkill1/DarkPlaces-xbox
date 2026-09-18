#!/usr/bin/env python3
"""Materialize Xbox memory limits from immutable classic engine headers."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile


EXPECTED = {
    "quakedef.h": "b76328fd266abeaafb83e5ff979d966951025e2b45f3c9f50fecdae047179c00",
    "netconn.h": "f1f277b5e1476b0be76642e71f340ce5ffb21b4d0fc300c347580751345d54de",
}

REPLACEMENTS = {
    "quakedef.h": (
        ("#define\tMAX_EDICTS\t\t32768", "#define\tMAX_EDICTS\t\t8192"),
        ("#define\tMAX_MODELS\t\t8192", "#define\tMAX_MODELS\t\t2048"),
        ("#define\tMAX_SOUNDS\t\t4096", "#define\tMAX_SOUNDS\t\t2048"),
        ('#include "netconn.h"', '#include "netconn_xbox.h"'),
    ),
    "netconn.h": (
        ("#define SERVERLIST_TOTALSIZE\t\t2048", "#define SERVERLIST_TOTALSIZE\t\t256"),
    ),
}

OUTPUT_NAMES = {
    "quakedef.h": "quakedef_xbox.h",
    "netconn.h": "netconn_xbox.h",
}


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as temporary:
            temporary.write(text)
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def materialize(source: Path, output_directory: Path) -> None:
    name = source.name
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if name not in EXPECTED or digest != EXPECTED[name]:
        raise SystemExit(f"unexpected pinned {name} identity: {digest}")
    text = data.decode("utf-8")
    for old, new in REPLACEMENTS[name]:
        if text.count(old) != 1:
            raise SystemExit(f"pinned {name} limit did not match exactly once: {old!r}")
        text = text.replace(old, new)
    _write_atomic(output_directory / OUTPUT_NAMES[name], text)


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(f"usage: {argv[0]} QUAKEDEF NETCONN OUTPUT_DIRECTORY", file=sys.stderr)
        return 2
    output_directory = Path(argv[3])
    materialize(Path(argv[1]), output_directory)
    materialize(Path(argv[2]), output_directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
