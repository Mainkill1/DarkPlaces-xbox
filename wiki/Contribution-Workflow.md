# Contribution Workflow

## Branch and PR shape

One PR should unlock one measurable gate. Avoid mixing toolchain changes, platform shims, renderer features, content conversions, and performance tuning unless they are inseparable for the stated gate.

## Required PR sections

1. Reason for the change.
2. Data/control flow before and after.
3. Supported Xbox feature or fallback affected.
4. Files and subsystem boundaries changed.
5. Exact build/test commands.
6. Desktop, xemu, and hardware results as applicable.
7. Memory/binary/performance effect.
8. Known limitations and follow-up issue.
9. License/source statement for any added asset or dependency.

Use `.github/PULL_REQUEST_TEMPLATE.md`.

## Regression policy

- `make sdl-release` must remain green.
- Xbox-only code must not accidentally change desktop render behavior.
- Backend fallbacks are visible in telemetry.
- A performance patch includes a baseline and candidate captured with the same content, camera, profile, and build type.
- Debug instrumentation must be compile-time or runtime controllable and must not silently remain in release measurements.

## Upstream sync

Keep Xbox changes isolated so upstream merges remain reviewable. Prefer:

- new platform/backend files;
- small additions to enums/object lists;
- compile guards at narrow boundaries;
- no formatting-only churn;
- no mass renames during bring-up.

Record upstream merge conflicts that reveal a weak boundary and improve the boundary rather than permanently carrying repeated manual conflict edits.
