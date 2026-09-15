#!/usr/bin/env python3
"""Create the Original Xbox port labels, milestones, issues, and master tracker.

The manifest is the reviewable source of truth. The script is intentionally
idempotent: it creates missing child issues, preserves existing child issue
bodies, and refreshes the master tracker from current issue state.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / ".github" / "port-issues.json"


class BootstrapError(RuntimeError):
    pass


def run_gh(
    method: str,
    endpoint: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    command = ["gh", "api", "--method", method, endpoint]
    input_text: str | None = None
    if payload is not None:
        command.extend(["--input", "-"])
        input_text = json.dumps(payload)

    completed = subprocess.run(
        command,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise BootstrapError(
            f"`{' '.join(command)}` failed with exit code "
            f"{completed.returncode}: {detail}"
        )

    output = completed.stdout.strip()
    return json.loads(output) if output else None


def get_all(endpoint: str) -> list[dict[str, Any]]:
    """Read all pages from an endpoint that returns a JSON list."""
    separator = "&" if "?" in endpoint else "?"
    page = 1
    results: list[dict[str, Any]] = []
    while True:
        batch = run_gh("GET", f"{endpoint}{separator}per_page=100&page={page}")
        if not isinstance(batch, list):
            raise BootstrapError(f"Expected a list from {endpoint}")
        results.extend(batch)
        if len(batch) < 100:
            return results
        page += 1


def load_manifest() -> dict[str, Any]:
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BootstrapError(f"Manifest not found: {MANIFEST_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise BootstrapError(f"Invalid JSON in {MANIFEST_PATH}: {exc}") from exc

    if manifest.get("schema_version") != 1:
        raise BootstrapError("Unsupported port issue manifest schema")
    if not manifest.get("issues"):
        raise BootstrapError("The port issue manifest has no child issues")
    return manifest


def validate_manifest(manifest: dict[str, Any]) -> None:
    label_names = [entry["name"] for entry in manifest["labels"]]
    if len(label_names) != len(set(label_names)):
        raise BootstrapError("Duplicate label names in the manifest")

    milestone_titles = [entry["title"] for entry in manifest["milestones"]]
    if len(milestone_titles) != len(set(milestone_titles)):
        raise BootstrapError("Duplicate milestone titles in the manifest")

    issues = manifest["issues"]
    keys = [entry["key"] for entry in issues]
    if len(keys) != len(set(keys)):
        raise BootstrapError("Duplicate issue keys in the manifest")

    titles = [entry["title"] for entry in issues]
    if len(titles) != len(set(titles)):
        raise BootstrapError("Duplicate issue titles in the manifest")

    known_keys: set[str] = set()
    all_keys = set(keys)
    known_labels = set(label_names)
    known_milestones = set(milestone_titles)

    for entry in issues:
        missing_labels = set(entry.get("labels", [])) - known_labels
        if missing_labels:
            raise BootstrapError(
                f"{entry['key']} uses unknown labels: "
                f"{', '.join(sorted(missing_labels))}"
            )
        if entry["milestone"] not in known_milestones:
            raise BootstrapError(
                f"{entry['key']} uses unknown milestone: {entry['milestone']}"
            )
        for dependency in entry.get("depends_on", []):
            if dependency not in all_keys:
                raise BootstrapError(
                    f"{entry['key']} depends on unknown issue key {dependency}"
                )
            if dependency not in known_keys:
                raise BootstrapError(
                    f"Issues are not topologically ordered: {entry['key']} "
                    f"appears before dependency {dependency}"
                )
        known_keys.add(entry["key"])


def ensure_labels(repo: str, manifest: dict[str, Any]) -> None:
    current = {
        entry["name"].casefold(): entry
        for entry in get_all(f"repos/{repo}/labels")
    }

    for wanted in manifest["labels"]:
        name = wanted["name"]
        payload = {
            "name": name,
            "color": wanted["color"].lstrip("#"),
            "description": wanted.get("description", ""),
        }
        existing = current.get(name.casefold())
        if existing is None:
            created = run_gh("POST", f"repos/{repo}/labels", payload)
            current[name.casefold()] = created
            print(f"created label: {name}")
            continue

        if (
            existing.get("color", "").casefold() != payload["color"].casefold()
            or (existing.get("description") or "") != payload["description"]
            or existing.get("name") != name
        ):
            encoded = urllib.parse.quote(existing["name"], safe="")
            run_gh("PATCH", f"repos/{repo}/labels/{encoded}", payload)
            print(f"updated label: {name}")


def ensure_milestones(
    repo: str, manifest: dict[str, Any]
) -> dict[str, int]:
    current = {
        entry["title"]: entry
        for entry in get_all(f"repos/{repo}/milestones?state=all")
    }

    result: dict[str, int] = {}
    for wanted in manifest["milestones"]:
        title = wanted["title"]
        payload = {
            "title": title,
            "description": wanted.get("description", ""),
            "state": "open",
        }
        existing = current.get(title)
        if existing is None:
            existing = run_gh("POST", f"repos/{repo}/milestones", payload)
            current[title] = existing
            print(f"created milestone: {title}")
        elif (
            (existing.get("description") or "") != payload["description"]
            or existing.get("state") != "open"
        ):
            existing = run_gh(
                "PATCH",
                f"repos/{repo}/milestones/{existing['number']}",
                payload,
            )
            current[title] = existing
            print(f"updated milestone: {title}")
        result[title] = int(existing["number"])
    return result


def marker(key: str) -> str:
    return f"<!-- xbox-port-key:{key} -->"


def bullet_lines(items: Iterable[str], checkbox: bool = False) -> str:
    prefix = "- [ ] " if checkbox else "- "
    return "\n".join(f"{prefix}{item}" for item in items)


def render_dependencies(
    entry: dict[str, Any],
    by_key: dict[str, dict[str, Any]],
) -> str:
    dependencies = entry.get("depends_on", [])
    if not dependencies:
        return "None."

    lines = []
    for key in dependencies:
        dependency = by_key[key]
        lines.append(
            f"- #{dependency['number']} — {dependency['title']}"
        )
    return "\n".join(lines)


def render_issue_body(
    entry: dict[str, Any],
    by_key: dict[str, dict[str, Any]],
    repo: str,
) -> str:
    sections = [
        marker(entry["key"]),
        "## Objective",
        entry["objective"],
        "## Context",
        entry["context"],
        "## Dependencies",
        render_dependencies(entry, by_key),
        "## Scope",
        bullet_lines(entry["scope"]),
        "## Acceptance criteria",
        bullet_lines(entry["acceptance"], checkbox=True),
        "## Required evidence",
        bullet_lines(entry["evidence"], checkbox=True),
    ]

    if entry.get("likely_files"):
        sections.extend(
            [
                "## Likely files and areas",
                bullet_lines(f"`{path}`" for path in entry["likely_files"]),
            ]
        )

    if entry.get("out_of_scope"):
        sections.extend(
            [
                "## Out of scope",
                bullet_lines(entry["out_of_scope"]),
            ]
        )

    sections.extend(
        [
            "## Planning references",
            (
                f"- [Port wiki](https://github.com/{repo}/wiki)\n"
                f"- [Roadmap](https://github.com/{repo}/wiki/Porting-Roadmap)\n"
                f"- [Issue map](https://github.com/{repo}/wiki/Issue-Map)\n"
                f"- Manifest key: `{entry['key']}`"
            ),
            (
                "_Do not close this issue with a compile-only claim. "
                "Attach or link the required evidence and identify the exact "
                "source, nxdk, content, and test environment revisions._"
            ),
        ]
    )
    return "\n\n".join(sections) + "\n"


def find_existing_issues(
    repo: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    entries = get_all(f"repos/{repo}/issues?state=all")
    issues = [entry for entry in entries if "pull_request" not in entry]
    by_key: dict[str, dict[str, Any]] = {}
    by_title: dict[str, dict[str, Any]] = {}

    for entry in issues:
        by_title[entry["title"]] = entry
        body = entry.get("body") or ""
        match_start = body.find("<!-- xbox-port-key:")
        if match_start >= 0:
            match_end = body.find(" -->", match_start)
            if match_end >= 0:
                key = body[match_start + len("<!-- xbox-port-key:") : match_end]
                by_key[key.strip()] = entry
    return by_key, by_title


def issue_snapshot(api_issue: dict[str, Any]) -> dict[str, Any]:
    return {
        "number": int(api_issue["number"]),
        "title": api_issue["title"],
        "url": api_issue["html_url"],
        "state": api_issue["state"],
    }


def ensure_child_issues(
    repo: str,
    manifest: dict[str, Any],
    milestone_numbers: dict[str, int],
) -> dict[str, dict[str, Any]]:
    existing_by_key, existing_by_title = find_existing_issues(repo)
    created_or_found: dict[str, dict[str, Any]] = {}

    for entry in manifest["issues"]:
        existing = existing_by_key.get(entry["key"])
        if existing is None:
            existing = existing_by_title.get(entry["title"])

        if existing is not None:
            created_or_found[entry["key"]] = issue_snapshot(existing)
            print(
                f"kept issue #{existing['number']}: {existing['title']}"
            )
            continue

        body = render_issue_body(entry, created_or_found, repo)
        payload = {
            "title": entry["title"],
            "body": body,
            "labels": entry["labels"],
            "milestone": milestone_numbers[entry["milestone"]],
        }
        created = run_gh("POST", f"repos/{repo}/issues", payload)
        created_or_found[entry["key"]] = issue_snapshot(created)
        existing_by_title[created["title"]] = created
        print(f"created issue #{created['number']}: {created['title']}")

    return created_or_found


def render_tracker_body(
    manifest: dict[str, Any],
    by_key: dict[str, dict[str, Any]],
    repo: str,
) -> str:
    tracker = manifest["tracker"]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in manifest["issues"]:
        grouped[entry["phase"]].append(entry)

    sections = [
        marker(tracker["key"]),
        tracker["summary"],
        "## Acceptance target",
        (
            "A deterministic, continuously looping mixed-workload world that "
            "runs in xemu and on a standard 64 MB retail Original Xbox, emits "
            "machine-readable results, and ships only redistributable content."
        ),
        "## Milestone gates",
    ]

    for milestone in manifest["milestones"]:
        phase = milestone["title"]
        lines = []
        for entry in grouped.get(phase, []):
            linked = by_key[entry["key"]]
            checked = "x" if linked["state"] == "closed" else " "
            lines.append(
                f"- [{checked}] #{linked['number']} — {entry['title']}"
            )
        sections.extend([f"### {phase}", "\n".join(lines)])

    sections.extend(
        [
            "## Source documents",
            (
                f"- [Wiki home](https://github.com/{repo}/wiki)\n"
                f"- [Port goals and scope]"
                f"(https://github.com/{repo}/wiki/Port-Goals-and-Scope)\n"
                f"- [Architecture]"
                f"(https://github.com/{repo}/wiki/Architecture)\n"
                f"- [Renderer strategy]"
                f"(https://github.com/{repo}/wiki/Renderer-Strategy)\n"
                f"- [Memory budget]"
                f"(https://github.com/{repo}/wiki/Memory-Budget)\n"
                f"- [Stress-world design]"
                f"(https://github.com/{repo}/wiki/Nexuiz-Stress-World)\n"
                f"- [Validation and telemetry]"
                f"(https://github.com/{repo}/wiki/Validation-and-Telemetry)"
            ),
            "## Tracker policy",
            (
                "The bootstrap workflow refreshes this checklist from current "
                "child-issue state. Child issue bodies are preserved after "
                "creation so investigation notes and evidence can accumulate."
            ),
        ]
    )
    return "\n\n".join(sections) + "\n"


def ensure_tracker(
    repo: str,
    manifest: dict[str, Any],
    by_key: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    existing_by_key, existing_by_title = find_existing_issues(repo)
    tracker = manifest["tracker"]
    existing = existing_by_key.get(tracker["key"])
    if existing is None:
        existing = existing_by_title.get(tracker["title"])

    body = render_tracker_body(manifest, by_key, repo)
    payload = {
        "title": tracker["title"],
        "body": body,
        "labels": tracker["labels"],
    }

    if existing is None:
        created = run_gh("POST", f"repos/{repo}/issues", payload)
        print(f"created tracker #{created['number']}: {created['title']}")
        return created

    updated = run_gh(
        "PATCH",
        f"repos/{repo}/issues/{existing['number']}",
        payload,
    )
    print(f"updated tracker #{updated['number']}: {updated['title']}")
    return updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate or bootstrap the Original Xbox port issue manifest."
        )
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate the manifest without calling GitHub",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_manifest()
    validate_manifest(manifest)

    if args.validate_only:
        print(
            f"valid manifest: {len(manifest['issues'])} child issues, "
            f"{len(manifest['labels'])} labels, and "
            f"{len(manifest['milestones'])} milestones"
        )
        return 0

    if not os.environ.get("GH_TOKEN") and not os.environ.get("GITHUB_TOKEN"):
        raise BootstrapError(
            "Set GH_TOKEN (preferred) or GITHUB_TOKEN before running."
        )
    if not os.environ.get("GH_TOKEN") and os.environ.get("GITHUB_TOKEN"):
        os.environ["GH_TOKEN"] = os.environ["GITHUB_TOKEN"]

    repo = os.environ.get("GITHUB_REPOSITORY") or manifest["repository"]
    metadata = run_gh("GET", f"repos/{repo}")
    if not metadata.get("has_issues", False):
        print(
            "\nGitHub Issues are disabled for this repository.\n"
            "Enable Settings -> General -> Features -> Issues, then rerun "
            "the 'Bootstrap Xbox port issues' workflow.\n",
            file=sys.stderr,
        )
        return 2

    print(f"bootstrapping Xbox port work in {repo}")
    ensure_labels(repo, manifest)
    milestone_numbers = ensure_milestones(repo, manifest)
    by_key = ensure_child_issues(repo, manifest, milestone_numbers)
    tracker_issue = ensure_tracker(repo, manifest, by_key)

    print(
        "\ncomplete: "
        f"{len(by_key)} child issues and tracker "
        f"#{tracker_issue['number']}\n"
        f"{tracker_issue['html_url']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BootstrapError as exc:
        print(f"bootstrap failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
