# Original Xbox Port Design

## Decision

Port modern DarkPlaces by preserving the engine's high-level game, VFS, QuakeC, visibility, model, particle, and material preparation code where practical, while adding explicit Original Xbox platform modules and a native `RENDERPATH_XBOX`.

The port does **not** treat nxdk SDL2 as an OpenGL implementation. SDL2 may provide input, audio, and 2D support, but 3D rendering is owned by an NV2A backend using nxdk/pbkit facilities.

## Acceptance product

The first product is not a feature-complete console game. It is a deterministic benchmark application that:

- boots as an XBE and XISO;
- loads a verified Nexuiz-derived content subset;
- moves one camera continuously through a connected world;
- transitions through geometry, texture, alpha/fur, particle, deformation/math, animation, lighting, combined, and recovery workloads;
- emits versioned machine-readable measurements;
- loops on xemu and a standard 64 MB retail Xbox.

## Source boundaries

### Retained engine responsibilities

- command/cvar and host lifecycle;
- virtual filesystem and package search;
- QuakeC VM and selected game logic;
- BSP/model parsing and visibility;
- entity, particle, and camera simulation;
- high-level render queue and material interpretation;
- demo/benchmark timing and result aggregation.

### Xbox platform responsibilities

- entry, timing, delay, shutdown, fatal display, and persistent diagnostics;
- launch path, read-only media, and writable result/config paths;
- controller input and hot-plug state;
- threading primitives or a deterministic single-thread fallback;
- audio output and an explicit no-audio mode;
- 64 MB budget enforcement and platform resource reporting.

### Xbox renderer responsibilities

- device and frame lifecycle;
- framebuffer, depth buffer, pushbuffer, synchronization, and present;
- static/transient vertex and index buffers;
- texture format conversion, upload, mipmaps, residency, and eviction;
- 2D console/menu/overlay;
- finite NV2A material recipes;
- geometry/model/particle submission;
- effect limits, fallbacks, counters, and diagnostics.

## Feature policy

Every selected content feature must resolve to one of five statuses:

1. **Native** — one supported NV2A recipe.
2. **Multipass** — multiple bounded passes with measured cost.
3. **Approximate** — visually different but workload-preserving fallback.
4. **Disabled** — intentionally removed from the Xbox profile.
5. **Deferred** — excluded from the first accepted benchmark.

Unknown combinations are errors or visible fallback materials. They must never silently select an unrelated shader.

## Memory policy

Standard 64 MB hardware is the only acceptance baseline. A 128 MB console is diagnostic-only. Budgets cover executable/static/stack, framebuffer/depth/pushbuffer, world/collision, textures/lightmaps, models/particles, audio, transients, and an emergency reserve. Every category reports current and peak usage.

Host-side asset conversion is preferred whenever it reduces runtime memory, conversion time, or unsupported-format risk without changing the intended workload.

## Determinism policy

Benchmark mode owns:

- fixed content/build/profile identities;
- simulation tick and interpolation policy;
- random seeds;
- camera path;
- workload marker order;
- warm-up and accepted sampling windows;
- loop transition;
- result schema.

Controller input cannot change the measured camera or simulation path. It may pause, resume, restart, skip to a marker outside accepted sampling, toggle diagnostics, write a snapshot, or exit.

## Failure policy

No unsupported service or render feature may fail as a silent hang. Errors include the build ID, last workload marker, frame, memory state, and specific failed operation where possible. The diagnostic path reserves memory and avoids recursive allocation.

## Validation authority

- Host CI proves source, manifest, and cross-compile integrity.
- xemu proves automated boot, completion, result extraction, and emulator regression use.
- Retail 64 MB hardware proves resource and long-run acceptance.
- Desktop DarkPlaces supplies a content/path reference, not a pixel-identical renderer oracle.

## Change rule

A pull request must name the issue it advances, the milestone gate it changes, its evidence, and any feature/memory/determinism impact. Compile-only proof cannot close a runtime acceptance issue.
