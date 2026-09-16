# Porting Roadmap

The phases are dependency gates. Later work may be researched in parallel, but it should not merge against an unproven earlier boundary. The live issue numbers below are the execution source of truth.

## Phase 0 — Architecture and reference

Issues [#2–#6](https://github.com/Mainkill1/DarkPlaces-xbox/issues/1):

- Apply approved [Option B](Playable-Game-and-LAN): fully playable offline Nexuiz plus LAN; benchmark mode remains included.
- Choose the renderer baseline from a working NV2A spike, not assumptions about SDL or OpenGL.
- Pin a reproducible desktop Nexuiz reference workload.
- Classify every source file and dependency for keep, gate, replace, or exclude.
- Establish source, content, and release provenance rules.

**Exit:** product scope, renderer direction, reference workload, source audit, and content policy are explicit and reviewable.

## Phase 1 — Toolchain and first engine boot

Issues [#7–#12](https://github.com/Mainkill1/DarkPlaces-xbox/issues/7):

- Pin nxdk and add an explicit Xbox link set.
- Add `DP_PLATFORM_XBOX` and capability-owned feature gates.
- Implement startup, monotonic timing, bounded logging, and fatal diagnostics.
- Define application, content, writable, and temporary filesystem roots.
- Package deterministic XBE/XISO artifacts and automate xemu boot observation.
- Reach normal `Host_Init` with a diagnosable engine console before full graphics work.

**Exit:** a clean checkout builds, packages, boots, identifies itself, mounts minimal legal data, executes a smoke command, and remains stable.

## Phase 2 — Retail-memory and runtime model

Issues [#13–#15](https://github.com/Mainkill1/DarkPlaces-xbox/issues/13):

- Measure executable, runtime, framebuffer, renderer, content, audio, stack, and temporary peaks.
- Replace generic `DP_SMALLMEMORY` guesses with an Xbox workload profile.
- Define the single-core task model and statically linked dependency policy.

**Exit:** the 64 MiB target has enforceable category budgets, preflight rejection, deterministic OOM evidence, and no accidental desktop loader/runtime model.

## Phase 3 — NV2A renderer and effects

Issues [#16–#22](https://github.com/Mainkill1/DarkPlaces-xbox/issues/16):

- Bring up video mode, framebuffer, present, timeout, and restart handling.
- Implement the core mesh/state backend with bounded pushbuffer and buffer ownership.
- Implement Xbox texture formats, mipmaps, conversion, and residency.
- Translate the finite material set into vertex programs/register combiners.
- Render BSP/lightmaps/sky/fog/alpha and then required models/effects.
- Add tiered water, reflection, shadow, fur/alpha stress, and GPU diagnostics.

**Exit:** the pinned map renders the required world, model, material, and effect subset with stable counters, known fallbacks, and reconciled memory.

## Phase 4 — Input, audio, and deterministic pacing

Issues [#23–#25](https://github.com/Mainkill1/DarkPlaces-xbox/issues/23):

- Add controller-operated diagnostics, free camera, abort, and recovery controls.
- Add bounded audio output/streaming or explicit benchmark modes that isolate its cost.
- Separate simulation and route progression from rendering speed and presentation waits.

**Exit:** the route is controllable but scored playback is input-safe, audio mode is explicit, and repeated runs produce the same timeline/checkpoint state.

## Phase 5 — Complete game, LAN, content and continuous stress world

[#35](https://github.com/Mainkill1/DarkPlaces-xbox/issues/35) adds controller-operated offline matches/campaign, real gamecode, audio and persistence. [#36](https://github.com/Mainkill1/DarkPlaces-xbox/issues/36) adds native LAN discovery/direct join/listen hosting and recovery. Both are release gates. Transport and platform work can run in parallel; a full-game run still depends on native rendering and actual content.

Issues [#26–#28](https://github.com/Mainkill1/DarkPlaces-xbox/issues/26):

- Pin the full Nexuiz Classic map/mode/campaign inventory and all required game assets, plus the benchmark route; publish coverage rather than silently omitting failures.
- Build one coherent map and slow route through geometry, texture, fuzz/alpha, math, particles, animation, lighting, water/reflection, audio, and combined-load districts.
- Add unattended warmup/run/loop state, watchdogs, bounded telemetry, durable summaries, and recovery evidence.

**Exit:** a full uninterrupted loop runs from a reproducible content package, covers every declared workload region, preserves deterministic checkpoints, and emits valid bounded results.

## Phase 6 — Regression, hardware, and release

Issues [#29–#30](https://github.com/Mainkill1/DarkPlaces-xbox/issues/29):

- Build tiered xemu gates from boot through the complete world loop.
- Compare only matching engine, nxdk, xemu, content, memory, video, effect, audio, and timing profiles.
- Validate short, 30-minute, multi-hour, and release-candidate soak runs on a stock-memory 64 MiB console with a homebrew-capable launch environment.
- Publish reproducible, legally approved artifacts, manifests, symbols, parsers, notices, and known limits.

**Exit:** complete offline/LAN matches, audio/persistence/controller recovery, full content coverage and the benchmark route pass xemu and retail-hardware acceptance. The release can be rebuilt and audited from declared inputs.
