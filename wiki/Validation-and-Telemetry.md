# Validation and Telemetry

## Playable-game acceptance

[Option B](Playable-Game-and-LAN) requires actual engine-linked offline and LAN matches, not only demo completion. Under #35/#36/#29/#30, test controller-only game setup, all required game actions, HUD/audio, death/respawn/scoring, map rotation, full content inventory, saved progression/preferences, LAN host and client roles, mismatched content, cable loss, failed joins and reconnects. Repeat on xemu and real stock-memory hardware.

Track diagnostic boot, first rendered map, completed offline match, completed LAN match and soak as separate gates. A unit-test service double, controller-only XBE or 60 FPS overlay cannot stand in for game execution. The user-provided foundation screenshot is diagnostic evidence only.

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
- audio preparation/mix time;
- active and mixed sound count;
- output-queue occupancy or low-water state;
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
- audio mode, mixed frames, mixer/decode timing and peak voices;
- audio underrun/low-water/stale-frame/emergency-read deltas;
- audio cache, codec and stream memory high-water;
- total memory high-water;
- first occurrence of any backend fallback or error.

Audio telemetry follows the [Xbox audio architecture](Xbox-Audio-Architecture). Callback code records fixed counters only; durable logging and interval summaries occur on the main thread. Audible, hardware-muted, simulated and no-audio runs are separate result identities.

## Output paths

Support at least one durable result path on real hardware, such as a writable Xbox drive directory. Add UDP/serial-style live reporting only after file output is reliable. Every file starts with build, nxdk, content-pack, content-audio manifest, audio mode, video-mode, profile, and hardware identifiers.

## Validation ladder

1. Desktop build remains green.
2. Xbox target compiles and links.
3. XBE boots in xemu and emits a startup marker.
4. Same XBE boots on hardware.
5. Each renderer rung has a controlled reference scene.
6. Selected BSP loads and survives camera traversal.
7. Fixed stereo audio passes tone, positional-effect, music-stream, loop and deliberate-underrun fixtures.
8. One complete loop produces valid results.
9. Repeated loops show stable memory, decoder, queue and game state.
10. One-hour soak passes on xemu and 64 MB hardware.
11. Complete offline/campaign and LAN host/client games pass #35/#36 with audio, persistence, recovery and content coverage.
12. Packaged release reproduces game and benchmark results from a clean checkout.

## Evidence storage

Port PRs should attach concise logs and link larger captures/artifacts. Results intended for long-term comparison belong under a structured evidence directory or release artifact, not pasted as an unreadable wall of frame rows.
