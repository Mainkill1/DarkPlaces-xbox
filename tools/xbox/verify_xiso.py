#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify an Original Xbox XDVDFS image against its staged disc tree.

The verifier reads XDVDFS metadata directly. It does not extract the image and
therefore adds only one sequential hash pass over packaged file payloads.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct
import sys

SECTOR = 2048
VOLUME_OFFSET = 32 * SECTOR
MAGIC = b"MICROSOFT*XBOX*MEDIA"
ATTR_DIRECTORY = 0x10
CHUNK = 1024 * 1024
MAX_DEPTH = 32
MAX_FILES = 200_000


class XisoError(ValueError):
    """The XDVDFS image is malformed or does not match the staged disc tree."""


@dataclass(frozen=True)
class XdvdfsEntry:
    path: str
    sector: int
    size: int
    attributes: int

    @property
    def offset(self) -> int:
        return self.sector * SECTOR


def _image_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError as exc:
        raise XisoError(f"cannot stat XISO {path}: {exc}") from exc


def _read_exact(stream, offset: int, length: int, label: str) -> bytes:
    if offset < 0 or length < 0:
        raise XisoError(f"invalid {label} extent")
    stream.seek(offset)
    data = stream.read(length)
    if len(data) != length:
        raise XisoError(f"truncated {label}")
    return data


def _safe_name(raw: bytes) -> str:
    if not raw or b"\x00" in raw or b"/" in raw or b"\\" in raw:
        raise XisoError("invalid XDVDFS filename")
    try:
        name = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise XisoError("non-ASCII XDVDFS filename in release image") from exc
    if name in (".", ".."):
        raise XisoError("invalid XDVDFS filename")
    return name


def read_xdvdfs(path: Path) -> dict[str, XdvdfsEntry]:
    path = path.resolve()
    size = _image_size(path)
    if size < VOLUME_OFFSET + SECTOR:
        raise XisoError("XISO is too small to contain an XDVDFS volume descriptor")

    files: dict[str, XdvdfsEntry] = {}
    folded_paths: set[str] = set()

    try:
        with path.open("rb") as stream:
            descriptor = _read_exact(stream, VOLUME_OFFSET, SECTOR, "volume descriptor")
            if descriptor[:20] != MAGIC or descriptor[0x7EC:0x800] != MAGIC:
                raise XisoError("XDVDFS volume descriptor magic is missing")
            root_sector, root_size = struct.unpack_from("<II", descriptor, 0x14)
            if root_sector == 0 or root_size == 0:
                raise XisoError("XDVDFS root directory is empty")

            active_tables: set[tuple[int, int]] = set()

            def walk_table(table_sector: int, table_size: int, prefix: str, depth: int) -> None:
                if depth > MAX_DEPTH:
                    raise XisoError("XDVDFS directory nesting exceeds verifier limit")
                table_offset = table_sector * SECTOR
                if table_size <= 0 or table_offset < 0 or table_offset + table_size > size:
                    raise XisoError(f"directory extent is outside image: {prefix or '/'}")
                table_key = (table_sector, table_size)
                if table_key in active_tables:
                    raise XisoError("recursive XDVDFS directory extent")
                active_tables.add(table_key)
                table = _read_exact(stream, table_offset, table_size, f"directory {prefix or '/'}")
                visited: set[int] = set()

                def walk_node(dword_offset: int) -> None:
                    byte_offset = dword_offset * 4
                    if byte_offset in visited:
                        raise XisoError(f"cycle in XDVDFS directory tree: {prefix or '/'}")
                    if byte_offset < 0 or byte_offset + 14 > len(table):
                        raise XisoError(f"directory node outside table: {prefix or '/'}")
                    visited.add(byte_offset)
                    left, right, data_sector, data_size, attrs, name_len = struct.unpack_from(
                        "<HHIIBB", table, byte_offset
                    )
                    if name_len == 0 or byte_offset + 14 + name_len > len(table):
                        raise XisoError(f"invalid directory entry length: {prefix or '/'}")
                    name = _safe_name(table[byte_offset + 14:byte_offset + 14 + name_len])
                    full = f"{prefix}/{name}" if prefix else name

                    if left:
                        walk_node(left)

                    extent_offset = data_sector * SECTOR
                    if data_size and (extent_offset < 0 or extent_offset + data_size > size):
                        raise XisoError(f"file extent outside XISO: {full}")
                    if attrs & ATTR_DIRECTORY:
                        if data_size:
                            walk_table(data_sector, data_size, full, depth + 1)
                    else:
                        folded = full.casefold()
                        if folded in folded_paths:
                            raise XisoError(f"duplicate/case-colliding XDVDFS path: {full}")
                        folded_paths.add(folded)
                        files[full] = XdvdfsEntry(full, data_sector, data_size, attrs)
                        if len(files) > MAX_FILES:
                            raise XisoError("XISO file count exceeds verifier limit")

                    if right:
                        walk_node(right)

                walk_node(0)
                active_tables.remove(table_key)

            walk_table(root_sector, root_size, "", 0)
    except OSError as exc:
        raise XisoError(f"cannot read XISO {path}: {exc}") from exc

    return files


def hash_extent(path: Path, entry: XdvdfsEntry) -> str:
    digest = hashlib.sha256()
    remaining = entry.size
    try:
        with path.open("rb") as stream:
            stream.seek(entry.offset)
            while remaining:
                block = stream.read(min(CHUNK, remaining))
                if not block:
                    raise XisoError(f"truncated XISO extent: {entry.path}")
                digest.update(block)
                remaining -= len(block)
    except OSError as exc:
        raise XisoError(f"cannot hash XISO extent {entry.path}: {exc}") from exc
    return digest.hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while block := stream.read(CHUNK):
                digest.update(block)
    except OSError as exc:
        raise XisoError(f"cannot hash staged file {path}: {exc}") from exc
    return digest.hexdigest()


def _staged_files(disc: Path) -> dict[str, Path]:
    if not disc.is_dir() or disc.is_symlink():
        raise XisoError(f"staged disc directory is missing or unsafe: {disc}")
    result: dict[str, Path] = {}
    folded: set[str] = set()
    for path in sorted(disc.rglob("*")):
        if path.is_symlink():
            raise XisoError(f"symlink is not allowed in staged disc tree: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise XisoError(f"non-regular staged disc entry: {path}")
        relative = path.relative_to(disc).as_posix()
        key = relative.casefold()
        if key in folded:
            raise XisoError(f"case-colliding staged path: {relative}")
        folded.add(key)
        result[relative] = path
    return result


def _read_extent_prefix(iso: Path, entry: XdvdfsEntry, length: int) -> bytes:
    try:
        with iso.open("rb") as stream:
            stream.seek(entry.offset)
            data = stream.read(min(length, entry.size))
    except OSError as exc:
        raise XisoError(f"cannot read XISO entry {entry.path}: {exc}") from exc
    return data


def verify_image(iso: Path, disc: Path) -> dict[str, int]:
    iso = iso.resolve()
    disc = disc.resolve()
    actual = read_xdvdfs(iso)
    expected = _staged_files(disc)
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        details = []
        if missing:
            details.append("missing=" + ",".join(missing[:20]))
        if extra:
            details.append("extra=" + ",".join(extra[:20]))
        raise XisoError("XISO file list differs from staged disc tree: " + " ".join(details))

    total = 0
    for relative, staged in expected.items():
        entry = actual[relative]
        staged_size = staged.stat().st_size
        if entry.size != staged_size:
            raise XisoError(f"size mismatch in XISO: {relative}")
        total += entry.size
        if relative.casefold() == "default.xbe":
            # The pinned extract-xiso substitutes only the last byte of this
            # media-check instruction (7d -> eb) while copying .xbe files.
            # Normalize the staged XBE by that exact transformation, then
            # require every packaged byte to match.
            with iso.open("rb") as image_stream:
                image_stream.seek(entry.offset)
                packaged_xbe = image_stream.read(entry.size)
            staged_xbe = staged.read_bytes()
            if packaged_xbe[:4] != b"XBEH" or len(packaged_xbe) < 0x128:
                raise XisoError("default.xbe inside XISO has invalid magic")
            if packaged_xbe[0x124:0x128] != staged_xbe[0x124:0x128]:
                raise XisoError("default.xbe memory flags differ inside XISO")
            normalized_xbe = staged_xbe.replace(
                b"\xe8\xca\xfd\xff\xff\x85\xc0\x7d",
                b"\xe8\xca\xfd\xff\xff\x85\xc0\xeb",
            )
            if packaged_xbe != normalized_xbe:
                raise XisoError("default.xbe payload differs inside XISO")
            continue
        if hash_extent(iso, entry) != _hash_file(staged):
            raise XisoError(f"payload hash mismatch in XISO: {relative}")

    return {"files": len(actual), "payload_bytes": total, "image_bytes": _image_size(iso)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("disc", type=Path)
    args = parser.parse_args(argv)
    try:
        summary = verify_image(args.iso, args.disc)
    except XisoError as exc:
        print(f"XISO verification error: {exc}", file=sys.stderr)
        return 2
    print(
        "XISO verified: "
        f"{summary['files']} files, {summary['payload_bytes']} payload bytes, "
        f"{summary['image_bytes']} image bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
