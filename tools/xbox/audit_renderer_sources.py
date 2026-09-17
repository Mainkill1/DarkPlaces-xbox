#!/usr/bin/env python3
"""Audit mutually exclusive bootstrap and native Xbox renderer ownership.

This is a source-contract audit. It does not compile, link, package, or execute
any renderer code.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ASSIGNMENT = re.compile(r"^([A-Za-z0-9_]+)\s*:?=\s*(.*)$")
REFERENCE = re.compile(r"\$\(([A-Za-z0-9_]+)\)")

NATIVE_REQUIRED = {
    "vid_xbox.c",
    "r_xbox_stats.c",
    "r_xbox_backend.c",
    "r_xbox_texture.c",
    "r_xbox_program.c",
    "r_xbox_material.c",
    "r_xbox_draw2d.c",
    "r_xbox_world.c",
    "r_xbox_models.c",
}
NATIVE_PROHIBITED = {
    "vid_xbox_bootstrap.c",
    "gl_backend.c",
    "gl_textures.c",
}
PRODUCTION_TOKENS = ("r_xbox_", "vid_xbox.c")


class AuditError(ValueError):
    """The renderer source contract is invalid."""


def _logical_lines(text: str) -> list[str]:
    lines: list[str] = []
    pending = ""
    for raw in text.splitlines():
        stripped = raw.split("#", 1)[0].rstrip()
        if not stripped and not pending:
            continue
        if stripped.endswith("\\"):
            pending += stripped[:-1] + " "
            continue
        lines.append((pending + stripped).strip())
        pending = ""
    if pending.strip():
        lines.append(pending.strip())
    return lines


def parse_make_variables(text: str) -> dict[str, str]:
    variables: dict[str, str] = {}
    for line in _logical_lines(text):
        match = ASSIGNMENT.match(line)
        if match:
            variables[match.group(1)] = match.group(2).strip()
    return variables


def expand_variable(
    name: str,
    variables: dict[str, str],
    stack: tuple[str, ...] = (),
) -> list[str]:
    if name in stack:
        raise AuditError("recursive make variable: " + " -> ".join((*stack, name)))
    if name not in variables:
        raise AuditError(f"missing make variable: {name}")

    value = variables[name]
    while True:
        match = REFERENCE.search(value)
        if match is None:
            break
        replacement = " ".join(
            expand_variable(match.group(1), variables, (*stack, name))
        )
        value = value[: match.start()] + replacement + value[match.end() :]
    return [token for token in value.split() if token]


def require_contains(path: Path, needle: str) -> None:
    if needle not in path.read_text(encoding="utf-8"):
        raise AuditError(f"{path}: missing required token {needle!r}")


def audit(root: Path, manifest: Path, mode: str) -> dict[str, object]:
    root = root.resolve()
    manifest = manifest.resolve()
    variables = parse_make_variables(manifest.read_text(encoding="utf-8"))

    for group in (
        "DP_XBOX_BOOTSTRAP_VIDEO_SRCS",
        "DP_XBOX_NATIVE_RENDER_SRCS",
        "DP_XBOX_HIGHLEVEL_RENDER_SRCS",
        "DP_XBOX_DORMANT_RENDER_SRCS",
        "DP_XBOX_BOOTSTRAP_SOURCES",
        "DP_XBOX_NATIVE_SOURCES",
    ):
        if group not in variables:
            raise AuditError(f"{manifest}: missing renderer group {group}")

    native_declared = set(expand_variable("DP_XBOX_NATIVE_RENDER_SRCS", variables))
    missing_native = sorted(NATIVE_REQUIRED - native_declared)
    if missing_native:
        raise AuditError("native renderer group is missing: " + ", ".join(missing_native))

    forbidden_declared = sorted(native_declared & NATIVE_PROHIBITED)
    if forbidden_declared:
        raise AuditError(
            "native renderer group contains prohibited owners: "
            + ", ".join(forbidden_declared)
        )

    resolved_name = (
        "DP_XBOX_NATIVE_SOURCES" if mode == "native" else "DP_XBOX_BOOTSTRAP_SOURCES"
    )
    resolved = expand_variable(resolved_name, variables)
    resolved_set = set(resolved)

    if len(resolved) != len(resolved_set):
        duplicates = sorted({item for item in resolved if resolved.count(item) > 1})
        raise AuditError("resolved source list contains duplicates: " + ", ".join(duplicates))

    if mode == "native":
        prohibited = sorted(resolved_set & NATIVE_PROHIBITED)
        if prohibited:
            raise AuditError(
                "native mode contains bootstrap/desktop owners: "
                + ", ".join(prohibited)
            )
        missing = sorted(NATIVE_REQUIRED - resolved_set)
        if missing:
            raise AuditError("native mode omits modules: " + ", ".join(missing))
    else:
        if "vid_xbox_bootstrap.c" not in resolved_set:
            raise AuditError("bootstrap mode does not contain vid_xbox_bootstrap.c")
        native_leaks = sorted(NATIVE_REQUIRED & resolved_set)
        if native_leaks:
            raise AuditError(
                "bootstrap mode contains native renderer modules: "
                + ", ".join(native_leaks)
            )

    require_contains(root / "vid.h", "RENDERPATH_XBOX")
    game_makefile = root / "xbox/game/Makefile"
    require_contains(game_makefile, "XBOX_RENDERER ?= bootstrap")
    require_contains(game_makefile, "-DDP_XBOX_NATIVE_RENDERER=1")
    require_contains(game_makefile, "XBOX_RENDERER must be native or bootstrap")

    for diagnostic in (root / "xbox/Makefile", root / "xbox/inputcheck/Makefile"):
        text = diagnostic.read_text(encoding="utf-8")
        for token in PRODUCTION_TOKENS:
            if token in text:
                raise AuditError(
                    f"{diagnostic}: production renderer token leaked into diagnostic: {token}"
                )

    return {
        "schema_version": 1,
        "mode": mode,
        "manifest": str(manifest.relative_to(root)),
        "resolved_count": len(resolved),
        "renderer_sources": sorted(
            source
            for source in resolved
            if source.startswith("r_xbox_") or source.startswith("vid_xbox")
        ),
        "prohibited_native_sources": sorted(NATIVE_PROHIBITED),
        "compile_link_runtime_verified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("bootstrap", "native"), required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        report = audit(args.root, args.manifest, args.mode)
    except (AuditError, OSError, UnicodeError) as exc:
        print(f"Xbox renderer source audit failed: {exc}", file=sys.stderr)
        return 2

    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
