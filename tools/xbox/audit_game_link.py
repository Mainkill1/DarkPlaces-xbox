#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Inventory the explicit Xbox source manifest. A source audit is NOT a link test."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

GROUPS = ("PLATFORM", "CORE", "CLIENT", "SERVER", "RESOURCE", "DORMANT_RENDER")
FORBIDDEN = {"sys_shared.c", "sys_sdl.c", "sys_null.c", "vid_sdl.c", "vid_null.c",
             "thread_sdl.c", "libcurl.c", "cl_video_libavw.c",
             "xbox/smoke/main.c", "xbox/inputcheck/main.c"}
REQUIRED = {"sys_xbox.c", "host.c", "fs.c", "cl_main.c", "sv_main.c", "prvm_exec.c",
            "menu.c", "netconn.c", "lhnet.c", "cl_attract.c", "cl_graphics_menu.c"}


def inspect(root: Path, manifest: Path) -> dict:
    text = manifest.read_text(encoding="utf-8")
    source = "\n".join(line.split("#", 1)[0] for line in text.splitlines()).replace("\\\n", " ")
    groups = {}
    for group in GROUPS:
        matches = re.findall(r"^DP_XBOX_" + group + r"_SRCS\s*:=([^\n]*)", source, re.MULTILINE)
        if len(matches) != 1:
            raise ValueError(f"expected exactly one literal source group {group}")
        groups[group.lower()] = matches[0].split()
    paths = [path for group in groups.values() for path in group]
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate source ownership")
    for path in paths:
        if not re.fullmatch(r"[a-zA-Z0-9_/.-]+\.c", path) or ".." in Path(path).parts or Path(path).is_absolute():
            raise ValueError(f"invalid literal source path: {path}")
        if path in FORBIDDEN:
            raise ValueError(f"forbidden source owner: {path}")
        if not (root / path).is_file():
            raise ValueError(f"missing source owner: {path}")
    if REQUIRED - set(paths):
        raise ValueError("missing required engine owners: " + ", ".join(sorted(REQUIRED - set(paths))))
    return {"profile": "engine-bootstrap", "required_mode": "-nexuiz", "groups": groups,
            "source_count": len(paths), "source_manifest_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "compiled": False, "linked": False, "booted": False, "playable": False,
            "bootstrap_backends": ["vid_xbox_bootstrap.c", "snd_null.c"],
            "native_renderer": False, "native_audio": False,
            "lan": "native socket/lifecycle source; sessions unverified",
            "dormant_renderer_note": "Upstream common symbol owners retained; no GL mode is enabled"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(inspect(args.root, args.manifest), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(f"Xbox source-manifest error: {error}")
