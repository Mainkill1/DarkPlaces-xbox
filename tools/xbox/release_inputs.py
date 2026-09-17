#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify the immutable external inputs used by the Xbox release candidate.

This tool performs no network access. It validates the repository-owned lock,
checks an already-downloaded Nexuiz 2.5.2 archive, and verifies exact Git
checkout revisions supplied by the caller.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any

SCHEMA_VERSION = 1
RELEASE = "nexuiz-xbox-2.5.2"
REPOSITORIES = {"nxdk", "darkplaces", "pbgl", "ogg", "vorbis"}
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX32 = re.compile(r"[0-9a-f]{32}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
CHUNK = 1024 * 1024


class ReleaseInputError(ValueError):
    """A release input is missing, mutable, malformed, or changed."""


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReleaseInputError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ReleaseInputError(
            f"{label} must contain exactly: {', '.join(sorted(expected))}"
        )
    return value


def _relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReleaseInputError(f"{label} must be a nonempty relative path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise ReleaseInputError(f"{label} must be a clean relative path: {value!r}")
    return value


def load_lock(path: Path) -> dict[str, Any]:
    try:
        lock = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseInputError(f"cannot read release lock {path}: {exc}") from exc

    _exact_keys(lock, {"schema_version", "release", "repositories", "content"}, "release lock")
    if lock["schema_version"] != SCHEMA_VERSION or lock["release"] != RELEASE:
        raise ReleaseInputError("unsupported release lock schema or release identity")

    repositories = lock["repositories"]
    if not isinstance(repositories, dict) or set(repositories) != REPOSITORIES:
        raise ReleaseInputError(
            "repositories must contain exactly: " + ", ".join(sorted(REPOSITORIES))
        )
    seen_paths: set[str] = set()
    for name, record in repositories.items():
        _exact_keys(record, {"repository", "commit", "path"}, f"repository {name}")
        if not isinstance(record["repository"], str) or not REPO.fullmatch(record["repository"]):
            raise ReleaseInputError(f"invalid repository name for {name}")
        if not isinstance(record["commit"], str) or not HEX40.fullmatch(record["commit"]):
            raise ReleaseInputError(f"{name} commit must be an exact lowercase 40-hex Git commit")
        checkout_path = _relative_path(record["path"], f"{name} path")
        if checkout_path.casefold() in seen_paths:
            raise ReleaseInputError(f"duplicate checkout path: {checkout_path}")
        seen_paths.add(checkout_path.casefold())

    content = _exact_keys(
        lock["content"], {"filename", "url", "sha256", "md5"}, "content"
    )
    if content["filename"] != "nexuiz-252.zip":
        raise ReleaseInputError("content filename must be nexuiz-252.zip")
    if not isinstance(content["url"], str) or not content["url"].startswith("https://"):
        raise ReleaseInputError("content URL must use HTTPS")
    if not isinstance(content["sha256"], str) or not HEX64.fullmatch(content["sha256"]):
        raise ReleaseInputError("content SHA-256 must be 64 lowercase hexadecimal characters")
    if not isinstance(content["md5"], str) or not HEX32.fullmatch(content["md5"]):
        raise ReleaseInputError("content MD5 must be 32 lowercase hexadecimal characters")
    return lock


def file_hashes(path: Path) -> tuple[str, str]:
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()
    try:
        with path.open("rb") as stream:
            while block := stream.read(CHUNK):
                sha256.update(block)
                md5.update(block)
    except OSError as exc:
        raise ReleaseInputError(f"cannot read {path}: {exc}") from exc
    return sha256.hexdigest(), md5.hexdigest()


def file_sha256(path: Path) -> str:
    return file_hashes(path)[0]


def verify_file(path: Path, expected_sha256: str) -> None:
    if not HEX64.fullmatch(expected_sha256):
        raise ReleaseInputError("expected SHA-256 is malformed")
    if not path.is_file():
        raise ReleaseInputError(f"required file does not exist: {path}")
    actual = file_sha256(path)
    if actual != expected_sha256:
        raise ReleaseInputError(
            f"SHA-256 mismatch for {path}: expected {expected_sha256}, got {actual}"
        )


def verify_content(path: Path, expected_sha256: str, expected_md5: str) -> None:
    if not HEX64.fullmatch(expected_sha256):
        raise ReleaseInputError("expected SHA-256 is malformed")
    if not HEX32.fullmatch(expected_md5):
        raise ReleaseInputError("expected MD5 is malformed")
    if not path.is_file():
        raise ReleaseInputError(f"required file does not exist: {path}")
    actual_sha256, actual_md5 = file_hashes(path)
    if actual_sha256 != expected_sha256:
        raise ReleaseInputError(
            f"SHA-256 mismatch for {path}: expected {expected_sha256}, got {actual_sha256}"
        )
    if actual_md5 != expected_md5:
        raise ReleaseInputError(
            f"MD5 mismatch for {path}: expected {expected_md5}, got {actual_md5}"
        )


def _git(path: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        raise ReleaseInputError(f"git verification failed for {path}: {detail}") from exc
    return proc.stdout.strip()


def verify_checkout(path: Path, expected_commit: str, require_clean: bool = False) -> None:
    if not HEX40.fullmatch(expected_commit):
        raise ReleaseInputError("expected Git commit is malformed")
    if not path.is_dir():
        raise ReleaseInputError(f"required checkout does not exist: {path}")
    actual = _git(path, "rev-parse", "HEAD")
    if actual != expected_commit:
        raise ReleaseInputError(
            f"checkout mismatch for {path}: expected {expected_commit}, got {actual}"
        )
    if require_clean and _git(path, "status", "--porcelain", "--untracked-files=no"):
        raise ReleaseInputError(f"tracked files are modified in dependency checkout: {path}")


def verify_checkouts(lock: dict[str, Any], root: Path) -> None:
    for name, record in lock["repositories"].items():
        path = root / record["path"]
        verify_checkout(path, record["commit"], require_clean=True)
        if name == "nxdk":
            bad = []
            status = _git(path, "submodule", "status", "--recursive")
            for line in status.splitlines():
                if line and line[0] in "-+U":
                    bad.append(line)
            if bad:
                raise ReleaseInputError(
                    "nxdk recursive submodules are not at recorded revisions:\n" + "\n".join(bad)
                )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lock",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "xbox" / "release" / "release-inputs.json",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify-lock")
    archive = sub.add_parser("verify-archive")
    archive.add_argument("archive", type=Path)
    checkouts = sub.add_parser("verify-checkouts")
    checkouts.add_argument("root", type=Path, help="repository root containing the locked checkout paths")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        lock = load_lock(args.lock)
        if args.command == "verify-archive":
            verify_content(
                args.archive,
                lock["content"]["sha256"],
                lock["content"]["md5"],
            )
        elif args.command == "verify-checkouts":
            verify_checkouts(lock, args.root.resolve())
    except ReleaseInputError as exc:
        print(f"release input error: {exc}", file=sys.stderr)
        return 2
    print(f"release inputs verified: {lock['release']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
