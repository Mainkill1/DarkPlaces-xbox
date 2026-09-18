#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Validate the staged Xbox disc tree before XDVDFS packaging."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any

RELEASE = "nexuiz-xbox-2.5.2"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
CHUNK = 1024 * 1024
STOCK_MAX_DIMENSION = 256
EXTERNAL_LIGHTMAP_DIMENSION = 64


class ReleaseTreeError(ValueError):
    """The staged release tree is incomplete, changed, or unsafe."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while block := stream.read(CHUNK):
                digest.update(block)
    except OSError as exc:
        raise ReleaseTreeError(f"cannot read {path}: {exc}") from exc
    return digest.hexdigest()


def _safe_relative(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ReleaseTreeError("manifest path must be a nonempty string")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ReleaseTreeError(f"unsafe manifest path: {value!r}")
    if "\\" in value or "\x00" in value:
        raise ReleaseTreeError(f"unsafe manifest path: {value!r}")
    return path.as_posix()


def _walk_files(root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    if not root.is_dir() or root.is_symlink():
        raise ReleaseTreeError(f"release directory is missing or unsafe: {root}")
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ReleaseTreeError(f"symlink is not allowed in release tree: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ReleaseTreeError(f"non-regular release entry: {path}")
        relative = path.relative_to(root).as_posix()
        folded = relative.casefold()
        if any(key.casefold() == folded for key in result):
            raise ReleaseTreeError(f"case-colliding release path: {relative}")
        result[relative] = path
    return result


def _load_content_identity(path: Path) -> dict[str, Any]:
    try:
        identity = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseTreeError(f"cannot read content identity: {exc}") from exc
    expected = {
        "schema_version", "release", "source_file", "source_sha256", "data_prefix",
        "source_file_count", "staged_file_count", "staged_bytes", "derived_content", "files",
    }
    if not isinstance(identity, dict) or set(identity) != expected:
        raise ReleaseTreeError("CONTENT-IDENTITY.json has an unexpected schema")
    if identity["schema_version"] != 2 or identity["release"] != RELEASE:
        raise ReleaseTreeError("CONTENT-IDENTITY.json has the wrong release identity")
    if not isinstance(identity["source_sha256"], str) or not HEX64.fullmatch(identity["source_sha256"]):
        raise ReleaseTreeError("CONTENT-IDENTITY.json source SHA-256 is malformed")
    if not isinstance(identity["files"], list) or not identity["files"]:
        raise ReleaseTreeError("CONTENT-IDENTITY.json contains no staged files")
    derived = identity["derived_content"]
    derived_keys = {
        "path", "profile", "max_dimension", "external_lightmap_dimension",
        "filter", "entry_storage",
        "asset_count", "bytes", "sha256",
    }
    if not isinstance(derived, dict) or set(derived) != derived_keys:
        raise ReleaseTreeError("derived content identity has an unexpected schema")
    if (
        derived["path"] != "data/zzzz-xbox-lowmem.pk3"
        or derived["profile"] != "stock64"
        or derived["max_dimension"] != STOCK_MAX_DIMENSION
        or derived["external_lightmap_dimension"] != EXTERNAL_LIGHTMAP_DIMENSION
        or derived["filter"] != "repeated-2x2-box-premultiplied-alpha"
        or derived["entry_storage"] != "stored"
        or type(derived["asset_count"]) is not int
        or derived["asset_count"] < 0
        or type(derived["bytes"]) is not int
        or derived["bytes"] <= 0
        or not isinstance(derived["sha256"], str)
        or not HEX64.fullmatch(derived["sha256"])
    ):
        raise ReleaseTreeError("derived content identity is malformed")
    return identity


def _verify_build_identity(path: Path, content_identity: Path) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ReleaseTreeError(f"cannot read build identity: {exc}") from exc
    fields: dict[str, str] = {}
    for line in lines:
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in fields:
            raise ReleaseTreeError(f"duplicate BUILD-IDENTITY field: {key}")
        fields[key] = value
    if fields.get("release") != RELEASE:
        raise ReleaseTreeError("BUILD-IDENTITY release does not match")
    expected_hash = _sha256(content_identity)
    if fields.get("content_identity_sha256") != expected_hash:
        raise ReleaseTreeError("BUILD-IDENTITY does not match CONTENT-IDENTITY.json")


def verify_tree(disc: Path) -> dict[str, int]:
    disc = disc.resolve()
    files = _walk_files(disc)
    required = {
        "default.xbe",
        "BUILD-IDENTITY.txt",
        "CONTENT-IDENTITY.json",
        "data/autoexec.cfg",
        "data/xbox-defaults.cfg",
    }
    missing = sorted(required - set(files))
    if missing:
        raise ReleaseTreeError("missing required release files: " + ", ".join(missing))

    xbe = files["default.xbe"]
    try:
        with xbe.open("rb") as stream:
            magic = stream.read(4)
    except OSError as exc:
        raise ReleaseTreeError(f"cannot read default.xbe: {exc}") from exc
    if magic != b"XBEH" or xbe.stat().st_size < 4096:
        raise ReleaseTreeError("default.xbe is not a plausible Xbox executable")

    content_path = files["CONTENT-IDENTITY.json"]
    identity = _load_content_identity(content_path)
    declared: dict[str, tuple[int, str]] = {}
    declared_bytes = 0
    for row in identity["files"]:
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
            raise ReleaseTreeError("content file record has an unexpected schema")
        relative = _safe_relative(row["path"])
        if not relative.startswith("data/"):
            raise ReleaseTreeError(f"content identity contains non-data path: {relative}")
        size = row["bytes"]
        digest = row["sha256"]
        if type(size) is not int or size < 0:
            raise ReleaseTreeError(f"invalid byte count for {relative}")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            raise ReleaseTreeError(f"invalid SHA-256 for {relative}")
        folded = relative.casefold()
        if any(name.casefold() == folded for name in declared):
            raise ReleaseTreeError(f"duplicate/case-colliding manifest path: {relative}")
        declared[relative] = (size, digest)
        declared_bytes += size

    actual_data = {name: path for name, path in files.items() if name.startswith("data/")}
    if set(actual_data) != set(declared):
        missing_data = sorted(set(declared) - set(actual_data))
        extra_data = sorted(set(actual_data) - set(declared))
        details = []
        if missing_data:
            details.append("missing=" + ",".join(missing_data))
        if extra_data:
            details.append("extra=" + ",".join(extra_data))
        raise ReleaseTreeError("staged data differs from content identity: " + " ".join(details))

    for relative, path in actual_data.items():
        size, digest = declared[relative]
        if path.stat().st_size != size:
            raise ReleaseTreeError(f"size mismatch for {relative}")
        if _sha256(path) != digest:
            raise ReleaseTreeError(f"SHA-256 mismatch for {relative}")

    if identity["staged_file_count"] != len(declared) or identity["staged_bytes"] != declared_bytes:
        raise ReleaseTreeError("content identity totals do not reconcile")
    derived = identity["derived_content"]
    derived_record = declared.get(derived["path"])
    if derived_record != (derived["bytes"], derived["sha256"]):
        raise ReleaseTreeError("derived content does not match its staged file record")
    pk3_files = sum(1 for name in declared if name.lower().endswith(".pk3"))
    if pk3_files < 1:
        raise ReleaseTreeError("release tree contains no Nexuiz PK3 files")

    _verify_build_identity(files["BUILD-IDENTITY.txt"], content_path)
    return {"data_files": len(declared), "pk3_files": pk3_files, "data_bytes": declared_bytes}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("disc", type=Path)
    args = parser.parse_args(argv)
    try:
        summary = verify_tree(args.disc)
    except ReleaseTreeError as exc:
        print(f"release tree error: {exc}", file=sys.stderr)
        return 2
    print(
        "release tree verified: "
        f"{summary['data_files']} data files, {summary['pk3_files']} PK3s, "
        f"{summary['data_bytes']} data bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
