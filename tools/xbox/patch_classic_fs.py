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

INFLATE_READ_ERROR_OLD = '''\
			if (error != Z_OK && error != Z_STREAM_END)
			{
				Con_Printf ("FS_Read: Can't inflate file\\n");
				break;
			}
'''

INFLATE_READ_ERROR_NEW = '''\
			if (error != Z_OK && error != Z_STREAM_END)
			{
				Con_Printf ("FS_Read: inflate error (result: %d, msg: %s)\\n",
					error, ztk->zstream.msg ? ztk->zstream.msg : "(null)");
				break;
			}
'''

LOAD_FILE_OLD = '''\
	fs_offset_t filesize = 0;

	file = FS_OpenVirtualFile(path, quiet);
'''

LOAD_FILE_NEW = '''\
	fs_offset_t filesize = 0;
	fs_offset_t readsize = 0;

	file = FS_OpenVirtualFile(path, quiet);
'''

LOAD_FILE_READ_OLD = '''\
		buf = (unsigned char *)Mem_Alloc (pool, filesize + 1);
		buf[filesize] = '\\0';
		FS_Read (file, buf, filesize);
		FS_Close (file);
		if (developer_loadfile.integer)
			Con_Printf("loaded file \\\"%s\\\" (%u bytes)\\n", path, (unsigned int)filesize);
'''

LOAD_FILE_READ_NEW = '''\
		buf = (unsigned char *)Mem_Alloc (pool, filesize + 1);
		buf[filesize] = '\\0';
		readsize = FS_Read (file, buf, filesize);
		if (readsize != filesize)
		{
			Xbox_MemoryTraceLoadFailure(path, filesize, readsize);
			Mem_Free(buf);
			buf = NULL;
			filesize = 0;
		}
		FS_Close (file);
		if (buf && developer_loadfile.integer)
			Con_Printf("loaded file \\\"%s\\\" (%u bytes)\\n", path, (unsigned int)filesize);
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
    if patched.count(INFLATE_READ_ERROR_OLD) != 2:
        raise SystemExit("pinned fs.c inflate read failures did not match exactly twice")
    patched = patched.replace(INFLATE_READ_ERROR_OLD, INFLATE_READ_ERROR_NEW)
    if patched.count(LOAD_FILE_OLD) != 1:
        raise SystemExit("pinned fs.c load-file locals did not match exactly once")
    patched = patched.replace(LOAD_FILE_OLD, LOAD_FILE_NEW)
    if patched.count(LOAD_FILE_READ_OLD) != 1:
        raise SystemExit("pinned fs.c load-file read did not match exactly once")
    patched = patched.replace(LOAD_FILE_READ_OLD, LOAD_FILE_READ_NEW)
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
