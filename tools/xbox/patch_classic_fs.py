#!/usr/bin/env python3
"""Materialize the one Xbox-specific fix required in pinned classic fs.c."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile


EXPECTED_SHA256 = "433ed0f346ece7a0d8920db4ec7a21ee60215070be01214e144c075cae69791e"

OLD = '''\
\t\tif (qz_inflateInit2 (&ztk->zstream, -MAX_WBITS) != Z_OK)
\t\t{
\t\t\tCon_Printf ("FS_OpenPackedFile: inflate init error (file: %s)\\n", pfile->name);
\t\t\tclose(dup_handle);
\t\t\tMem_Free(file);
\t\t\treturn NULL;
\t\t}
'''

NEW = '''\
\t\t{
\t\t\tint inflate_result = qz_inflateInit2 (&ztk->zstream, -MAX_WBITS);
\t\t\tif (inflate_result != Z_OK)
\t\t\t{
\t\t\t\tCon_Printf ("FS_OpenPackedFile: inflate init error (result: %d, window: %d, stream size: %u, zalloc: %s, zfree: %s, msg: %s, file: %s)\\n",
\t\t\t\t\tinflate_result, -MAX_WBITS, (unsigned int)sizeof(ztk->zstream),
\t\t\t\t\tztk->zstream.zalloc ? "set" : "null",
\t\t\t\t\tztk->zstream.zfree ? "set" : "null",
\t\t\t\t\tztk->zstream.msg ? ztk->zstream.msg : "(null)", pfile->name);
\t\t\t\tclose(dup_handle);
\t\t\t\tMem_Free(ztk);
\t\t\t\tMem_Free(file);
\t\t\t\treturn NULL;
\t\t\t}
\t\t}
'''


def materialize(source: Path, output: Path) -> None:
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"unexpected pinned fs.c identity: {digest}")
    text = data.decode("utf-8")
    if text.count(OLD) != 1:
        raise SystemExit("pinned fs.c inflate failure block did not match exactly once")
    patched = text.replace(OLD, NEW)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=output.name + ".", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as temporary:
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
