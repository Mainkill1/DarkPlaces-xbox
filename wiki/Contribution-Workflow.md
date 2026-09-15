# Contribution Workflow

## Branch and PR shape

One PR should unlock one measurable gate. Avoid mixing toolchain changes, platform shims, renderer features, content conversions, and performance tuning unless they are inseparable for the stated gate.

The live work queue is the [master port epic](https://github.com/Mainkill1/DarkPlaces-xbox/issues/1). Extend or split those issues instead of creating a parallel roadmap.

## Required PR sections

1. Reason for the change.
2. Data/control flow before and after.
3. Supported Xbox feature or fallback affected.
4. Files and subsystem boundaries changed.
5. Exact build/test commands.
6. Desktop, cross-build, xemu, and hardware results as applicable.
7. Memory, binary-size, and performance effect.
8. Workload/profile identity for any benchmark result.
9. Known limitations and follow-up issue.
10. License/source statement for any added asset or dependency.

Use `.github/PULL_REQUEST_TEMPLATE.md`.

## Documentation location

Canonical port documentation lives under `wiki/` and is published to the GitHub Wiki from that directory. Some initial issue text names `docs/xbox-port/...`; satisfy those deliverables by updating the corresponding wiki page or adding a new page linked from `wiki/Home.md`. Do not create a second port-documentation hierarchy.

Keep `wiki/Issue-Map.md` synchronized whenever an issue is added, replaced, split, or retired.

## Regression policy

- `make sdl-release` must remain green.
- Xbox-only code must not accidentally change desktop render behavior.
- Backend fallbacks, caps, and quality tiers are visible in telemetry.
- A performance patch includes baseline and candidate captures with identical source, nxdk, content, route, profile, build type, xemu/hardware, and measurement settings.
- Debug instrumentation must be compile-time or runtime controllable and must not silently remain in release measurements.
- Compile-only evidence cannot satisfy boot, render, content, complete-loop, or hardware gates.

## Upstream sync

Keep Xbox changes isolated so upstream merges remain reviewable. Prefer:

- new platform/backend files;
- small additions to enums/object lists;
- compile guards at narrow boundaries;
- no formatting-only churn;
- no mass renames during bring-up.

Record upstream merge conflicts that reveal a weak boundary and improve the boundary rather than permanently carrying repeated manual conflict edits.
