#!/usr/bin/env python3
"""Verify that an nxdk checkout matches the revision pinned by this port."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def normalize_sha(value: str) -> str:
    """Return a normalized full Git SHA or raise ValueError."""

    normalized = value.strip().lower()
    if not _FULL_SHA.fullmatch(normalized):
        raise ValueError(
            "expected a full 40-character hexadecimal Git commit SHA, "
            f"got {value!r}"
        )
    return normalized


def check_revision(
    expected: str,
    actual: str,
    allow_mismatch: bool = False,
) -> tuple[bool, str]:
    """Compare two normalized revisions and describe the decision."""

    expected_sha = normalize_sha(expected)
    actual_sha = normalize_sha(actual)
    if expected_sha == actual_sha:
        return True, f"nxdk revision matches pinned commit {expected_sha}"

    message = (
        "nxdk revision mismatch: "
        f"expected {expected_sha}, actual {actual_sha}"
    )
    if allow_mismatch:
        return True, f"development override accepted; {message}"
    return False, message


def _run_git(nxdk_dir: Path, arguments: Sequence[str]) -> str:
    completed = subprocess.run(
        ["git", "-C", str(nxdk_dir), *arguments],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            f"git command failed in {nxdk_dir}: {detail or 'unknown error'}"
        )
    return completed.stdout.strip()


def read_pin(pin_file: Path) -> str:
    try:
        return normalize_sha(pin_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"nxdk pin file does not exist: {pin_file}") from exc


def checkout_revision(nxdk_dir: Path) -> str:
    if not nxdk_dir.is_dir():
        raise RuntimeError(f"nxdk directory does not exist: {nxdk_dir}")
    return normalize_sha(_run_git(nxdk_dir, ["rev-parse", "HEAD"]))


def checkout_has_tracked_changes(nxdk_dir: Path) -> bool:
    output = _run_git(
        nxdk_dir,
        ["status", "--porcelain", "--untracked-files=no"],
    )
    return bool(output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pin-file",
        type=Path,
        required=True,
        help="file containing the required full nxdk commit SHA",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--nxdk-dir",
        type=Path,
        help="nxdk Git checkout to inspect",
    )
    source.add_argument(
        "--actual-sha",
        help="explicit actual SHA, primarily for automation and tests",
    )
    parser.add_argument(
        "--allow-mismatch",
        action="store_true",
        help="accept a non-pinned revision for an explicitly unscored development build",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="accept tracked changes in the nxdk checkout",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        expected = read_pin(args.pin_file)
        if args.actual_sha is not None:
            actual = normalize_sha(args.actual_sha)
        else:
            actual = checkout_revision(args.nxdk_dir)

        ok, message = check_revision(
            expected,
            actual,
            allow_mismatch=args.allow_mismatch,
        )
        stream = sys.stdout if ok else sys.stderr
        print(message, file=stream)
        if not ok:
            return 3

        if (
            args.nxdk_dir is not None
            and not args.allow_dirty
            and checkout_has_tracked_changes(args.nxdk_dir)
        ):
            print(
                "nxdk checkout contains tracked modifications; "
                "use --allow-dirty only for an explicitly unscored development build",
                file=sys.stderr,
            )
            return 4
    except (RuntimeError, ValueError) as exc:
        print(f"nxdk verification failed: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
