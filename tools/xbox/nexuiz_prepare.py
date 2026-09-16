#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Inventory local Nexuiz Classic PK3s and stage an explicit, unconverted subset.

Python 3.10+; standard library only. This does not download, execute, or approve
assets, infer dependency closure, convert NV2A resources, or build an Xbox game.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import BinaryIO
import zipfile
import zlib
from autoplay_config import build_config

RELEASE = "nexuiz-classic-2.5.2"
VERSION = 1
CHUNK = 1024 * 1024
MAX_ENTRIES = 65535
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class ContentError(ValueError):
    """Invalid, changed, or unsupported preparation input."""


def text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContentError(f"{label} must be a nonempty string")
    return value


def keys(value: object, expected: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise ContentError(f"{label} must contain exactly: {', '.join(sorted(expected))}")
    return value


def positive(value: object, label: str) -> int:
    if type(value) is not int or not 0 < value < 2**31:
        raise ContentError(f"{label} must be an integer from 1 to 2147483647")
    return value


def virtual_path(value: object) -> str:
    name = text(value, "asset path")
    if (not name.isascii() or len(name.encode("ascii")) >= 128
            or any(ord(c) < 32 or ord(c) == 127 or c in '\\:*?"<>|' for c in name)
            or any(p in ("", ".", "..") for p in name.split("/"))):
        raise ContentError(f"invalid virtual path: {name!r}")
    return name


def source_name(value: object) -> str:
    name = virtual_path(value)
    if "/" in name or not name.lower().endswith(".pk3"):
        raise ContentError(f"source must be a PK3 filename in --data-dir: {name!r}")
    return name


def sha(value: object) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ContentError("sha256 must contain 64 lowercase hexadecimal characters")
    return value


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def stream_hash(stream: BinaryIO) -> str:
    stream.seek(0)
    result = hashlib.sha256()
    while block := stream.read(CHUNK):
        result.update(block)
    stream.seek(0)
    return result.hexdigest()


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return stream_hash(stream)


def data_root(path: Path) -> Path:
    if not path.is_dir():
        raise ContentError(f"data directory does not exist: {path}")
    return path.resolve()


def open_source(root: Path, name: str, stack: ExitStack) -> BinaryIO:
    path = root / source_name(name)
    if path.is_symlink() or not path.is_file():
        raise ContentError(f"source must be a regular, non-symlink file: {name}")
    stream = stack.enter_context(path.open("rb"))
    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
        raise ContentError(f"not a regular file: {name}")
    return stream


def archive_index(pack: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    entries = pack.infolist()
    if len(entries) > MAX_ENTRIES:
        raise ContentError("archive exceeds classic PK3 entry limit")
    names: dict[str, zipfile.ZipInfo] = {}
    folded: set[str] = set()
    for entry in entries:
        name = virtual_path(entry.filename[:-1] if entry.is_dir() else entry.filename)
        if entry.orig_filename != entry.filename:
            raise ContentError("archive contains a NUL-truncated name")
        if name.casefold() in folded:
            raise ContentError(f"archive case/duplicate collision: {name}")
        folded.add(name.casefold())
        mode = entry.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ContentError(f"archive symlink is not supported: {name}")
        if entry.flag_bits & 1 or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise ContentError(f"encrypted or unsupported compression: {name}")
        if not entry.is_dir():
            names[name] = entry
    return names


def transfer(pack: zipfile.ZipFile, entry: zipfile.ZipInfo, limit: int,
             target: BinaryIO | None = None) -> str:
    if entry.file_size > limit:
        raise ContentError(f"asset budget exceeded: {entry.filename}")
    count = 0
    result = hashlib.sha256()
    with pack.open(entry) as source:
        while block := source.read(CHUNK):
            count += len(block)
            if count > limit or count > entry.file_size:
                raise ContentError(f"asset size mismatch: {entry.filename}")
            result.update(block)
            if target is not None:
                target.write(block)
    if count != entry.file_size:
        raise ContentError(f"asset size mismatch: {entry.filename}")
    return result.hexdigest()


def inventory(root: Path, max_asset_bytes: int, max_total_bytes: int) -> dict:
    root = data_root(root)
    positive(max_asset_bytes, "asset budget")
    positive(max_total_bytes, "total budget")
    paths = sorted(p.name for p in root.iterdir() if p.suffix.lower() == ".pk3")
    if not paths:
        raise ContentError("no PK3 files found; pass the extracted Nexuiz data directory")
    if len(paths) != len({p.casefold() for p in paths}):
        raise ContentError("source filename case collision")
    sources = []
    owners: dict[str, list[str]] = {}
    total = 0
    for name in paths:
        with ExitStack() as stack:
            stream = open_source(root, name, stack)
            before = stream_hash(stream)
            pack = stack.enter_context(zipfile.ZipFile(stream))
            assets = []
            for path, entry in sorted(archive_index(pack).items()):
                total += entry.file_size
                if total > max_total_bytes:
                    raise ContentError("inventory total budget exceeded")
                assets.append({"path": path, "bytes": entry.file_size,
                               "sha256": transfer(pack, entry, max_asset_bytes)})
                owners.setdefault(path.casefold(), []).append(name)
            if stream_hash(stream) != before:
                raise ContentError(f"source changed during inventory: {name}")
            sources.append({"file": name, "sha256": before, "assets": assets})
    return {"schema_version": VERSION, "release": RELEASE, "xbox_ready": False,
            "sources": sources, "uncompressed_bytes": total,
            "cross_pack_paths": {p: names for p, names in sorted(owners.items()) if len(names) > 1}}


def reject_duplicates(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContentError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_selection(path: Path) -> dict:
    plan = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
    if isinstance(plan, dict):
        plan.setdefault("notices", [])
    keys(plan, {"schema_version", "release", "profile", "max_asset_bytes",
                "max_total_bytes", "sources", "assets", "notices"}, "selection")
    if type(plan["schema_version"]) is not int or plan["schema_version"] != VERSION or plan["release"] != RELEASE:
        raise ContentError("unsupported schema_version or release")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", text(plan["profile"], "profile")):
        raise ContentError("profile must be a lowercase identifier")
    positive(plan["max_asset_bytes"], "asset budget")
    positive(plan["max_total_bytes"], "total budget")
    for field in ("sources", "assets"):
        if not isinstance(plan[field], list) or not 0 < len(plan[field]) <= MAX_ENTRIES:
            raise ContentError(f"{field} must be a nonempty, bounded list")
    sources = set()
    for source in plan["sources"]:
        keys(source, {"file", "sha256", "origin"}, "source")
        name = source_name(source["file"])
        sha(source["sha256"])
        text(source["origin"], "origin")
        if name.casefold() in sources:
            raise ContentError(f"source collision: {name}")
        sources.add(name.casefold())
    names = set()
    for asset in plan["assets"]:
        keys(asset, {"path", "source", "sha256", "license", "attribution", "notice"}, "asset")
        name = virtual_path(asset["path"])
        source_name(asset["source"])
        sha(asset["sha256"])
        text(asset["license"], "license")
        text(asset["attribution"], "attribution")
        virtual_path(asset["notice"])
        if name.casefold() in names:
            raise ContentError(f"selected path collision: {name}")
        names.add(name.casefold())
    if not isinstance(plan["notices"], list) or len(plan["assets"]) + len(plan["notices"]) > MAX_ENTRIES:
        raise ContentError("notices must be a bounded list")
    for notice in plan["notices"]:
        keys(notice, {"file", "path", "sha256", "origin"}, "notice")
        virtual_path(notice["file"])
        name = virtual_path(notice["path"])
        sha(notice["sha256"])
        text(notice["origin"], "notice origin")
        if name.casefold() in names:
            raise ContentError(f"notice path collision: {name}")
        names.add(name.casefold())
    selected = {a["path"] for a in plan["assets"] + plan["notices"]}
    for asset in plan["assets"]:
        if asset["notice"] not in selected:
            raise ContentError(f"license notice must also be selected: {asset['notice']}")
    if {s["file"] for s in plan["sources"]} != {a["source"] for a in plan["assets"]}:
        raise ContentError("selected source set must exactly match declared sources")
    plan["sources"].sort(key=lambda s: s["file"])
    plan["assets"].sort(key=lambda a: a["path"])
    plan["notices"].sort(key=lambda a: a["path"])
    return plan


def stage(root: Path, selection: Path, output: Path, notice_dir: Path | None = None,
          demos: list[str] | None = None, require_autoplay: bool = False) -> dict:
    root = data_root(root)
    plan = load_selection(selection)
    try:
        demo_names, config = build_config([a["path"] for a in plan["assets"]], demos, require_autoplay)
    except ValueError as exc:
        raise ContentError(str(exc)) from exc
    generated = []
    if config is not None:
        if any(a["path"].casefold() == "xbox-benchmark.cfg" for a in plan["assets"] + plan["notices"]):
            raise ContentError("selected content collides with generated xbox-benchmark.cfg")
        if len(config) > plan["max_asset_bytes"]:
            raise ContentError("autoplay configuration exceeds asset budget")
        generated = [{"path": "xbox-benchmark.cfg", "payload": config}]
    if len(plan["assets"]) + len(plan["notices"]) + len(generated) > MAX_ENTRIES:
        raise ContentError("generated content exceeds classic PK3 entry limit")
    if output.exists() or output.is_symlink():
        raise ContentError(f"output already exists; choose a new directory: {output}")
    if output.resolve().is_relative_to(root):
        raise ContentError("output must be outside the source data directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        opened = {}
        for source in plan["sources"]:
            stream = open_source(root, source["file"], stack)
            if stream_hash(stream) != source["sha256"]:
                raise ContentError(f"source hash mismatch: {source['file']}")
            pack = stack.enter_context(zipfile.ZipFile(stream))
            opened[source["file"]] = (stream, pack, archive_index(pack))
        total = sum(len(a["payload"]) for a in generated)
        for asset in plan["assets"]:
            entry = opened[asset["source"]][2].get(asset["path"])
            if entry is None:
                raise ContentError(f"missing asset: {asset['path']} in {asset['source']}")
            if entry.file_size > plan["max_asset_bytes"]:
                raise ContentError(f"asset budget exceeded: {asset['path']}")
            total += entry.file_size
        notices = {}
        if plan["notices"]:
            notice_root = data_root(notice_dir or selection.parent)
            for notice in plan["notices"]:
                path = notice_root / notice["file"]
                parts = Path(notice["file"]).parts
                if (any(notice_root.joinpath(*parts[:i]).is_symlink() for i in range(1, len(parts) + 1))
                        or not path.is_file()):
                    raise ContentError(f"notice must be a regular non-symlink file: {notice['file']}")
                stream = stack.enter_context(path.open("rb"))
                size = os.fstat(stream.fileno()).st_size
                if size > plan["max_asset_bytes"]:
                    raise ContentError(f"notice asset budget exceeded: {notice['file']}")
                if stream_hash(stream) != notice["sha256"]:
                    raise ContentError(f"notice hash mismatch: {notice['file']}")
                notices[notice["path"]] = (stream, size)
                total += size
        if total > plan["max_total_bytes"]:
            raise ContentError("selected total budget exceeded")
        with tempfile.TemporaryDirectory(prefix=".nexuiz-prep-", dir=output.parent) as temporary:
            staging = Path(temporary)
            (staging / "data").mkdir()
            package = staging / "data/xboxprep.pk3"
            assets = []
            notice_records = []
            files = sorted(plan["assets"] + plan["notices"] + generated, key=lambda a: a["path"])
            with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as dest:
                for item in files:
                    info = zipfile.ZipInfo(item["path"], date_time=(1980, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    with dest.open(info, "w") as target:
                        if "payload" in item:
                            target.write(item["payload"])
                        elif "source" in item:
                            _, pack, entries = opened[item["source"]]
                            entry = entries[item["path"]]
                            actual = transfer(pack, entry, plan["max_asset_bytes"], target)
                            if actual != item["sha256"]:
                                raise ContentError(f"asset hash mismatch: {item['path']}")
                            assets.append(dict(item, bytes=entry.file_size))
                        else:
                            stream, size = notices[item["path"]]
                            stream.seek(0)
                            result = hashlib.sha256()
                            count = 0
                            while block := stream.read(CHUNK):
                                count += len(block)
                                if count > size:
                                    raise ContentError(f"notice changed: {item['file']}")
                                result.update(block)
                                target.write(block)
                            if count != size or result.hexdigest() != item["sha256"]:
                                raise ContentError(f"notice hash mismatch: {item['file']}")
                            notice_records.append(dict(item, bytes=size))
            for source in plan["sources"]:
                if stream_hash(opened[source["file"]][0]) != source["sha256"]:
                    raise ContentError(f"source changed during staging: {source['file']}")
            with zipfile.ZipFile(package) as check:
                if check.testzip() is not None:
                    raise ContentError("output package failed CRC verification")
            manifest = {"schema_version": VERSION, "release": RELEASE, "profile": plan["profile"],
                        "xbox_ready": False, "conversion": "none-byte-preserving",
                        "tool_sha256": file_hash(Path(__file__)),
                        "selection_sha256": hashlib.sha256(encoded(plan)).hexdigest(),
                        "sources": plan["sources"], "assets": assets, "notices": notice_records, "selected_bytes": total,
                        "generated_files": [{"path": a["path"], "bytes": len(a["payload"]),
                                             "sha256": hashlib.sha256(a["payload"]).hexdigest(),
                                             "generator": "autoplay_config.py"} for a in generated],
                        "autoplay": {"configured": config is not None, "demos": demo_names,
                                     "generator_sha256": file_hash(Path(__file__).with_name("autoplay_config.py")),
                                     "xbox_boot_tested": False},
                        "package": "data/xboxprep.pk3", "package_bytes": package.stat().st_size,
                        "package_sha256": file_hash(package),
                        "validation": {"dependency_closure": "not-checked",
                                       "material_compatibility": "not-checked",
                                       "runtime_memory": "not-measured",
                                       "licensing": "caller-supplied-declarations"}}
            (staging / "manifest.json").write_bytes(encoded(manifest))
            if output.exists() or output.is_symlink():
                raise ContentError(f"output appeared during staging: {output}")
            staging.rename(output)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("inventory", help="hash all files in local source PK3s")
    scan.add_argument("--data-dir", type=Path, required=True)
    scan.add_argument("--output", type=Path, required=True)
    scan.add_argument("--max-asset-bytes", type=int, default=64 * CHUNK)
    scan.add_argument("--max-total-bytes", type=int, default=2047 * CHUNK)
    build = commands.add_parser("stage", help="stage an explicit selection, without conversion")
    build.add_argument("--data-dir", type=Path, required=True)
    build.add_argument("--selection", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--notice-dir", type=Path, help="external notice root; defaults to selection directory")
    build.add_argument("--demo", action="append", help="selected .dem path; repeat to specify playlist order")
    build.add_argument("--require-autoplay", action="store_true", help="reject a package with no selected demos")
    args = parser.parse_args(argv)
    try:
        if args.command == "inventory":
            report = inventory(args.data_dir, args.max_asset_bytes, args.max_total_bytes)
            with args.output.open("xb") as output:
                output.write(encoded(report))
        else:
            stage(args.data_dir, args.selection, args.output, args.notice_dir, args.demo, args.require_autoplay)
    except (ContentError, json.JSONDecodeError, OSError, UnicodeError, zipfile.BadZipFile, zipfile.LargeZipFile,
            EOFError, RuntimeError, NotImplementedError, zlib.error) as exc:
        print(f"Nexuiz preparation failed: {exc}", file=sys.stderr)
        return 2
    print(f"Prepared {args.output}; Xbox compatibility and memory fit are NOT established.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
