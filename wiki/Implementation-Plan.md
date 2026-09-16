# Implementation Plan

The executable work plan is the [master port epic](https://github.com/Mainkill1/DarkPlaces-xbox/issues/1) and its child issues #2–#30 plus #35 (offline gameplay) and #36 (LAN). Issue bodies own dependencies, acceptance criteria, and required evidence. This page defines how those issues should be implemented and merged.

## Gate 0 — Architecture and reference

1. Apply [Option B](Playable-Game-and-LAN): complete offline Nexuiz plus LAN, audio and persistence, retaining the benchmark. Do not keep obsolete benchmark-only exclusions.
2. Produce the NV2A renderer-baseline spike before selecting the production architecture.
3. Freeze a desktop reference workload, inputs, configuration, checkpoints, and output schema.
4. Complete the source/dependency and licensing audits.
5. Record decisions in the wiki rather than leaving them only in issue comments.

Do not begin a production renderer against an undefined content set or unproven translation boundary.

## Gate 1 — Toolchain and first engine boot

1. Pin nxdk and create the canonical Xbox build entry point.
2. Add explicit platform identity and a first-link source/capability profile.
3. Implement early startup, monotonic timing, debug output, persistent bounded logs, and fatal records.
4. Implement packaged-content and writable-root discovery.
5. Build deterministic XBE/XISO artifacts and an xemu startup observer.
6. Reach normal DarkPlaces `Host_Init`, execute a smoke command, and idle stably.

Do not treat a successful cross-link as a boot milestone.

## Gate 2 — Retail-memory runtime

1. Measure the actual post-runtime memory envelope.
2. Define category ceilings and preserve an emergency diagnostic margin.
3. Instrument current/peak allocations and contiguous/GPU-visible failures.
4. Audit and replace generic `DP_SMALLMEMORY` limits from measured workload needs.
5. Lock the initial single-core task model and static dependency set.
6. Preflight content before expensive decode/upload work.

Do not accept a renderer or content milestone with unexplained memory, hidden quality reduction, or nondeterministic OOM behavior.

## Gate 3 — Renderer bring-up

1. Bring up video, clear, present, synchronization, timeout, and restart.
2. Implement mesh/index buffers, transforms, state caching, validation, and bounded pushbuffer use.
3. Implement textures, mipmaps, upload, residency, conversion, and eviction.
4. Render 2D diagnostics before depending on graphics for failure visibility.
5. Render BSP world/lightmaps/visibility, then models/animation.
6. Resolve the pinned material set to finite NV2A programs and explicit fallbacks.
7. Add particles/sprites/decals/beams/lights.
8. Add tiered water/reflection/shadow/fur workloads and per-pass diagnostics.

Each step must preserve previous reference fixtures. Unsupported features remain visible and counted until a reviewed recipe or fallback replaces them.

## Gate 4 — Input, audio, and deterministic pacing

1. Add controller diagnostics, free camera, menu/console navigation, abort, and recovery.
2. Lock out incidental input during scored playback.
3. Add the selected audio backend and bounded decode/stream policy.
4. Separate real-time soak mode from uncapped throughput mode.
5. Pin random seeds, warmup, route start, loop boundary, checkpoints, and state markers.
6. Report simulation/update, render preparation/submission, present/wait, and total frame time separately.

Do not publish performance results until workload progression is independent of frame rate and result profiles identify every timing/audio mode.

## Gate 5 — Complete game, LAN and benchmark

Before release, #35 must complete real offline matches/campaign paths with audio, saved state and controller UI. #36 must complete LAN discovery/direct joining/listen hosting, map transitions and reconnect. Keep the native game client/server/VM link and measure their combined memory. Socket work may proceed in parallel with the renderer, but end-to-end game evidence depends on both. The first rendered map is an intermediate gate.

1. Acquire and hash approved source content.
2. Inventory the entire pinned game map/mode/campaign corpus and dependencies, then the additional benchmark world. Record every item tested, blocked or explicitly excepted; do not silently narrow to one working demo.
3. Convert Xbox-ready assets deterministically and preserve source/license traceability.
4. Select or author the continuous world and versioned camera spline.
5. Define workload targets and invalidating caps/fallbacks for every region.
6. Add unattended preflight, warmup, looping, watchdog recovery, bounded telemetry, and durable summaries.
7. Verify the loop seam does not accumulate memory, entities, effects, decals, audio, or storage.

The standard profile is frozen only after counters prove every intended region is active; screenshots alone are insufficient.

## Gate 6 — Acceptance and release

1. Automate tiered xemu execution from build/package through the complete loop.
2. Preserve compact failure bundles and reject mismatched profiles.
3. Validate complete offline/LAN matches, campaign/progression where supplied, all inventoried maps/modes, save/relaunch, network/controller recovery, the full benchmark loop and extended soak on retail 64 MiB hardware.
4. Profile and remove accidental port overhead without weakening workload coverage.
5. Build a manifest-approved release containing only redistributable files and required notices.

## Pull request slicing

A normal pull request should satisfy one child issue or one independently reviewable acceptance slice. Large issues such as BSP, textures, materials, content conversion, or telemetry may use multiple PRs, but each PR must leave a runnable state and update the issue checklist with evidence.

Recommended commit order inside a PR:

1. failing validation/reference case;
2. minimal implementation;
3. xemu evidence;
4. hardware evidence when required by that issue;
5. documentation, feature matrix, and memory-budget update.

## Completion source of truth

The GitHub issue tracker records execution status. Wiki pages record durable design. Result/evidence packages record proof. None substitutes for the other two.
