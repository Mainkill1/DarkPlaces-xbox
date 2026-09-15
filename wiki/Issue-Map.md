# Issue Map

The live execution plan is [issue #1](https://github.com/Mainkill1/DarkPlaces-xbox/issues/1). The issue bodies own dependencies, deliverables, acceptance criteria, and required evidence. This page is the durable navigation map and must be updated when issues are split, replaced, or added.

Do not run or create a second roadmap beside these issues.

## Epic

- [#1 — Port DarkPlaces/Nexuiz stress world to the original Xbox](https://github.com/Mainkill1/DarkPlaces-xbox/issues/1)

## Phase 0 — Architecture and reference

- [#2 — Define the Xbox MVP, compatibility promise, and explicit exclusions](https://github.com/Mainkill1/DarkPlaces-xbox/issues/2)
- [#3 — Choose the renderer baseline with an NV2A proof-of-concept](https://github.com/Mainkill1/DarkPlaces-xbox/issues/3)
- [#4 — Capture a reproducible desktop Nexuiz reference workload](https://github.com/Mainkill1/DarkPlaces-xbox/issues/4)
- [#5 — Audit every subsystem and dependency for the Xbox link set](https://github.com/Mainkill1/DarkPlaces-xbox/issues/5)
- [#6 — Establish the source, content, and release licensing policy](https://github.com/Mainkill1/DarkPlaces-xbox/issues/6)

**Gate:** the MVP is bounded, the desktop reference is pinned, the source/dependency matrix is complete, content policy is enforceable, and a renderer direction has working NV2A evidence.

## Phase 1 — Toolchain and first engine boot

- [#7 — Add a pinned nxdk toolchain and first-class Xbox build target](https://github.com/Mainkill1/DarkPlaces-xbox/issues/7)
- [#8 — Add Xbox platform identity, compile-time feature gates, and portability checks](https://github.com/Mainkill1/DarkPlaces-xbox/issues/8)
- [#9 — Implement the Xbox system backend: startup, timing, logging, and fatal errors](https://github.com/Mainkill1/DarkPlaces-xbox/issues/9)
- [#10 — Implement Xbox filesystem roots, packaged content, saves, and logs](https://github.com/Mainkill1/DarkPlaces-xbox/issues/10)
- [#11 — Package XBE/XISO artifacts and automate xemu boot validation](https://github.com/Mainkill1/DarkPlaces-xbox/issues/11)
- [#12 — Milestone: boot an XBE through Host_Init with a diagnosable engine console](https://github.com/Mainkill1/DarkPlaces-xbox/issues/12)

**Gate:** a clean checkout builds, packages, boots, reaches normal DarkPlaces host initialization, mounts legal minimal data, and preserves diagnostics before a production renderer exists.

## Phase 2 — Retail-memory and runtime model

- [#13 — Define and enforce a measured 64 MiB memory budget](https://github.com/Mainkill1/DarkPlaces-xbox/issues/13)
- [#14 — Replace generic DP_SMALLMEMORY defaults with an Xbox load and capacity profile](https://github.com/Mainkill1/DarkPlaces-xbox/issues/14)
- [#15 — Define the Xbox thread, task-queue, and static dependency model](https://github.com/Mainkill1/DarkPlaces-xbox/issues/15)

**Gate:** major allocations have owners and ceilings, over-budget content fails predictably, the 64 MiB profile can be enforced in xemu, and no desktop dynamic-library assumptions reach the XBE.

## Phase 3 — NV2A renderer and effects

- [#16 — Implement the Xbox video-mode, framebuffer, and present backend](https://github.com/Mainkill1/DarkPlaces-xbox/issues/16)
- [#17 — Implement the core NV2A mesh backend and render-state translation](https://github.com/Mainkill1/DarkPlaces-xbox/issues/17)
- [#18 — Implement Xbox texture formats, swizzling, mipmaps, and bounded residency](https://github.com/Mainkill1/DarkPlaces-xbox/issues/18)
- [#19 — Replace GLSL permutations with a bounded NV2A material program set](https://github.com/Mainkill1/DarkPlaces-xbox/issues/19)
- [#20 — Render BSP worlds with lightmaps, sky, fog, alpha, and visibility culling](https://github.com/Mainkill1/DarkPlaces-xbox/issues/20)
- [#21 — Render animated models, sprites, particles, decals, beams, and dynamic lights](https://github.com/Mainkill1/DarkPlaces-xbox/issues/21)
- [#22 — Add tiered water, reflections, shadows, fur/alpha stress, and GPU diagnostics](https://github.com/Mainkill1/DarkPlaces-xbox/issues/22)

**Gate:** a real pinned map renders stable world, model, material, and effect output; required workload features have explicit NV2A recipes or approved fallbacks; resource use reconciles with the memory budget.

## Phase 4 — Input, audio, and deterministic pacing

- [#23 — Implement Xbox controller input and benchmark-safe controls](https://github.com/Mainkill1/DarkPlaces-xbox/issues/23)
- [#24 — Implement bounded Xbox audio output and streaming](https://github.com/Mainkill1/DarkPlaces-xbox/issues/24)
- [#25 — Make demo playback, camera motion, and frame pacing deterministic](https://github.com/Mainkill1/DarkPlaces-xbox/issues/25)

**Gate:** the appliance is operable without a keyboard, incidental input cannot alter scored playback, audio cost and mode are explicit, and repeated runs hit the same timeline checkpoints independent of render speed.

## Phase 5 — Content and continuous stress world

- [#26 — Pin Nexuiz content and build a reproducible Xbox asset pipeline](https://github.com/Mainkill1/DarkPlaces-xbox/issues/26)
- [#27 — Build one continuous mixed-world flythrough and autoplay loop](https://github.com/Mainkill1/DarkPlaces-xbox/issues/27)
- [#28 — Add unattended looping, watchdog recovery, and machine-readable telemetry](https://github.com/Mainkill1/DarkPlaces-xbox/issues/28)

**Gate:** approved source content reproducibly builds an Xbox-ready package; one uninterrupted map and route exercise every required workload region; loops, watchdog events, and results are deterministic, durable, and bounded.

## Phase 6 — Regression, hardware, and release

- [#29 — Build the xemu regression harness and first complete demo gate](https://github.com/Mainkill1/DarkPlaces-xbox/issues/29)
- [#30 — Validate retail hardware, complete soak testing, and publish the first stress-suite release](https://github.com/Mainkill1/DarkPlaces-xbox/issues/30)

**Gate:** the complete route passes the tiered xemu harness, an unmodified 64 MiB Xbox passes the declared route and soak criteria, and the release is reproducible and license-clean.
