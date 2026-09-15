# Validation and Telemetry

## Result goals

FPS alone is not enough. Vsync and frame caps can hide improvements or regressions. Record work and timing directly.

## Minimum per-frame data

- frame number and loop number;
- workload marker;
- total frame time;
- simulation/update time;
- render-queue/build time;
- GPU submission time where measurable;
- present/wait time;
- draw calls;
- submitted triangles/vertices;
- texture uploads and uploaded bytes;
- material fallback counts;
- current/peak memory totals.

## Per-zone summary

For each marker interval report:

- frames;
- average, median, p95, p99, and maximum frame time;
- dropped/over-budget frames;
- draw/triangle/texture totals;
- memory high-water;
- first occurrence of any backend fallback or error.

## Output paths

Support at least one durable result path on real hardware, such as a writable Xbox drive directory. Add UDP/serial-style live reporting only after file output is reliable. Every file starts with build, nxdk, content-pack, video-mode, profile, and hardware identifiers.

## Validation ladder

1. Desktop build remains green.
2. Xbox target compiles and links.
3. XBE boots in xemu and emits a startup marker.
4. Same XBE boots on hardware.
5. Each renderer rung has a controlled reference scene.
6. Selected BSP loads and survives camera traversal.
7. One complete loop produces valid results.
8. Repeated loops show stable memory and state.
9. One-hour soak passes on xemu and 64 MB hardware.
10. Packaged release reproduces the result from a clean checkout.

## Evidence storage

Port PRs should attach concise logs and link larger captures/artifacts. Results intended for long-term comparison belong under a structured evidence directory or release artifact, not pasted as an unreadable wall of frame rows.
