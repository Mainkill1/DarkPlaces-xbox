#!/usr/bin/env python3
"""Materialize exact trailer-byte accounting for the pinned classic allocator."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile


EXPECTED_SHA256 = "fa09ff1852c67bcf71c751272c328057828198d2305af7d78f2b3647411accfb"


def _replace_exact(text: str, old: str, new: str, count: int) -> str:
    if text.count(old) != count:
        raise SystemExit(f"pinned zone.c pattern did not match {count} time(s): {old}")
    return text.replace(old, new)


def materialize(source: Path, output: Path) -> None:
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"unexpected pinned zone.c identity: {digest}")
    text = data.decode("utf-8")
    text = _replace_exact(
        text,
        "#if MEMCLUMPING\n#define MEMCLUMP_SENTINEL 0xABADCAFE\n#endif",
        "#if MEMPARANOIA\n#define XBOX_ZONE_TRAILER_BYTES sizeof(unsigned int)\n"
        "#else\n#define XBOX_ZONE_TRAILER_BYTES sizeof(unsigned char)\n#endif\n\n"
        "#if MEMCLUMPING\n#define MEMCLUMP_SENTINEL 0xABADCAFE\n#endif",
        1,
    )
    text = _replace_exact(
        text, "sizeof(memheader_t) + size + sizeof(unsigned int)",
        "sizeof(memheader_t) + size + XBOX_ZONE_TRAILER_BYTES", 1,
    )
    text = _replace_exact(
        text, "sizeof(memheader_t) + size + sizeof(unsigned char)",
        "sizeof(memheader_t) + size + XBOX_ZONE_TRAILER_BYTES", 1,
    )
    text = _replace_exact(
        text, "sizeof(memheader_t) + size + sizeof(sentinel2)",
        "sizeof(memheader_t) + size + XBOX_ZONE_TRAILER_BYTES", 2,
    )
    text = _replace_exact(
        text, "sizeof(memheader_t) + size + 1",
        "sizeof(memheader_t) + size + XBOX_ZONE_TRAILER_BYTES", 2,
    )
    text = _replace_exact(
        text, "sizeof(memheader_t) + mem->size + sizeof(int)",
        "sizeof(memheader_t) + mem->size + XBOX_ZONE_TRAILER_BYTES", 3,
    )
    text = _replace_exact(
        text,
        '\t\tif (mem == NULL)\n'
        '\t\t\tSys_Error("Mem_Alloc: out of memory (alloc at %s:%i)", filename, fileline);',
        '\t\tif (mem == NULL)\n'
        '\t\t\tSys_Error("Mem_Alloc: out of memory (%lu bytes in pool %s at %s:%i)", '
        '(unsigned long)size, pool->name, filename, fileline);',
        1,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=output.name + ".", dir=output.parent
    )
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
