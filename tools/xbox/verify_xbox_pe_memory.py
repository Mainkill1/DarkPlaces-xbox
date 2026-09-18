#!/usr/bin/env python3
"""Reject Xbox PE images whose static footprint crowds the 64 MiB target."""

from pathlib import Path
import struct
import sys


MAX_IMAGE_BYTES = 24 * 1024 * 1024


def pe_image_size(path: Path) -> int:
    data = path.read_bytes()
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("missing DOS header")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    optional = pe_offset + 24
    if optional + 60 > len(data) or data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise ValueError("missing PE header")
    if struct.unpack_from("<H", data, optional)[0] != 0x10B:
        raise ValueError("expected PE32 optional header")
    return struct.unpack_from("<I", data, optional + 56)[0]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} MAIN.EXE", file=sys.stderr)
        return 2
    path = Path(argv[1])
    try:
        image_size = pe_image_size(path)
    except (OSError, ValueError, struct.error) as error:
        print(f"invalid Xbox PE image {path}: {error}", file=sys.stderr)
        return 2
    if image_size > MAX_IMAGE_BYTES:
        print(
            f"Xbox PE image is {image_size} bytes; exceeds {MAX_IMAGE_BYTES}-byte limit",
            file=sys.stderr,
        )
        return 1
    print(
        f"Xbox PE static image: {image_size} bytes "
        f"({MAX_IMAGE_BYTES - image_size} bytes below limit)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
