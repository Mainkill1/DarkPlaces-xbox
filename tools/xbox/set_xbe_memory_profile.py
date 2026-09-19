#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Set the pinned cxbe XBE's 64 MiB runtime-limit bit for a release profile."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile


FLAGS_OFFSET = 0x124
LIMIT_64_MIB = 0x4
EXPECTED_OTHER_FLAGS = 0x1  # cxbe mounts the utility drive.


class XbeProfileError(ValueError):
    pass


def set_profile(path: Path, profile: str) -> int:
    if profile not in ("stock64", "dev128"):
        raise XbeProfileError(f"unsupported content profile: {profile}")
    try:
        data = bytearray(path.read_bytes())
    except OSError as exc:
        raise XbeProfileError(f"cannot read XBE: {exc}") from exc
    if len(data) < 4096 or data[:4] != b"XBEH":
        raise XbeProfileError("not a plausible XBE")
    flags = int.from_bytes(data[FLAGS_OFFSET:FLAGS_OFFSET + 4], "little")
    if flags & ~LIMIT_64_MIB != EXPECTED_OTHER_FLAGS:
        raise XbeProfileError(f"unexpected cxbe initialization flags: 0x{flags:08x}")
    desired = EXPECTED_OTHER_FLAGS | (LIMIT_64_MIB if profile == "stock64" else 0)
    if flags == desired:
        return desired
    data[FLAGS_OFFSET:FLAGS_OFFSET + 4] = desired.to_bytes(4, "little")
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as temporary:
            temporary.write(data)
        os.chmod(temporary_name, path.stat().st_mode & 0o777)
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return desired


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xbe", type=Path)
    parser.add_argument("profile", choices=("stock64", "dev128"))
    args = parser.parse_args(argv)
    try:
        flags = set_profile(args.xbe, args.profile)
    except XbeProfileError as exc:
        print(f"XBE memory profile error: {exc}", file=sys.stderr)
        return 2
    print(f"XBE memory profile={args.profile} initialization_flags=0x{flags:08x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
