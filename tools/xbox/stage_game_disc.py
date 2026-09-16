#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Stage an already prepared, hash-pinned Nexuiz package beside the game XBE.

Does not download content or manufacture license declarations. This validates
packaging inputs, not Xbox playability. Invoke during a build, not at runtime.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import zipfile
import zlib

MAX_PACKAGE = 512 * 1024 * 1024
MAX_FILE = 64 * 1024 * 1024
SHA = re.compile(r"[0-9a-f]{64}\Z")
REQUIRED_BOOT = {"default.cfg", "progs.dat", "menu.dat", "xbox-benchmark.cfg"}


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def content_check(root: Path) -> tuple[Path, dict]:
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("CONTENT_DIR needs the preparation tool's manifest.json")
    if manifest_path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("preparation manifest is unexpectedly large")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("preparation manifest must be a JSON object")
    if manifest.get("release") != "nexuiz-classic-2.5.2":
        raise ValueError("expected a Nexuiz Classic 2.5.2 preparation manifest")
    if manifest.get("package") != "data/xboxprep.pk3":
        raise ValueError("expected package path data/xboxprep.pk3")
    package = root / "data/xboxprep.pk3"
    if (root / "data").is_symlink() or package.is_symlink() or not package.is_file():
        raise ValueError("prepared PK3 must be a regular file")
    expected = manifest.get("package_sha256", "")
    if not isinstance(expected, str) or not SHA.fullmatch(expected):
        raise ValueError("missing or invalid package SHA-256")
    if package.stat().st_size > MAX_PACKAGE:
        raise ValueError("package exceeds bootstrap host-staging limit")
    if digest(package) != expected:
        raise ValueError("prepared PK3 no longer matches its manifest")
    names = set()
    total = 0
    with zipfile.ZipFile(package) as archive:
        if len(archive.infolist()) > 65535:
            raise ValueError("too many package entries")
        for item in archive.infolist():
            path = item.filename
            if (not path.isascii() or len(path) >= 128 or "\\" in path or
                    any(part in ("", ".", "..") for part in path.split("/")) or
                    any(ord(c) < 32 or ord(c) == 127 or c in ':*?"<>|' for c in path)):
                raise ValueError(f"invalid virtual asset path: {path!r}")
            if item.orig_filename != path or path.casefold() in names:
                raise ValueError(f"duplicate or truncated virtual path: {path!r}")
            names.add(path.casefold())
            if item.flag_bits & 1 or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError(f"encrypted/symlink entry: {path}")
            if item.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise ValueError(f"unsupported PK3 compression: {path}")
            total += item.file_size
            if item.file_size > MAX_FILE or total > MAX_PACKAGE:
                raise ValueError("expanded package exceeds bootstrap staging limits")
        missing = REQUIRED_BOOT - names
        if missing:
            raise ValueError("missing required real game/bootstrap files: " + ", ".join(sorted(missing)))
        if not any(path.endswith(".dem") for path in names):
            raise ValueError("the prepared autoplay package has no selected demo")
        if archive.testzip() is not None:
            raise ValueError("input package CRC failure")
    return package, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content", type=Path, required=True)
    parser.add_argument("--disc", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    source, manifest = content_check(args.content.resolve())
    if args.check_only:
        print("Game content packaging prerequisites present; runtime compatibility unverified")
        return
    if args.disc is None:
        parser.error("--disc is required when staging")
    disc = args.disc.resolve()
    if (disc == args.content.resolve() or disc.is_relative_to(args.content.resolve())
            or args.content.resolve().is_relative_to(disc)):
        raise ValueError("disc output must not overlap source content")
    disc.mkdir(parents=True, exist_ok=True)
    unexpected_root = {p.name for p in disc.iterdir()} - {"data", "default.xbe"}
    if unexpected_root:
        raise ValueError("disc contains unmanaged files: " + ", ".join(sorted(unexpected_root)))
    target = disc / "data"
    if target.is_symlink():
        raise ValueError("disc data directory must not be a symlink")
    # Only manage the known data subtree; never remove the XBE or unrelated data.
    if target.exists():
        unexpected = {p.name for p in target.iterdir()} - {"xboxprep.pk3"}
        if unexpected:
            raise ValueError("disc contains unmanaged data: " + ", ".join(sorted(unexpected)))
    target.mkdir(exist_ok=True)
    final = target / "xboxprep.pk3"
    if final.is_symlink():
        raise ValueError("disc package must not be a symlink")
    if not final.exists() or digest(final) != manifest["package_sha256"]:
        descriptor, temporary = tempfile.mkstemp(prefix="package-", dir=disc.parent)
        os.close(descriptor)
        try:
            shutil.copyfile(source, temporary)
            if digest(Path(temporary)) != manifest["package_sha256"]:
                raise ValueError("source changed while staging")
            os.replace(temporary, final)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
    # Evidence stays outside the ISO directory to avoid recursive repacking.
    record = disc.parent / "content-identity.json"
    value = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if not record.exists() or record.read_text() != value:
        record.write_text(value)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, zipfile.BadZipFile, zipfile.LargeZipFile,
            RuntimeError, EOFError, NotImplementedError, zlib.error) as error:
        raise SystemExit(f"Game content staging failed: {error}")
