# Retail 64 MiB Memory Architecture Design

**Status:** Approved architecture for implementation on `port/nexuiz-playable-lan`.

**Scope:** Memory ownership and accounting for the playable Original Xbox port, with immediate focus on the native renderer. This design must shape later texture, geometry, audio, LAN, and content work; it is not a renderer-effect or gameplay feature specification.

## Objective

Make the stock 64 MiB Xbox the primary memory constraint from the start. The port must measure actual memory remaining after platform/video initialization, reserve recovery headroom, avoid allocator fragmentation, reject over-budget workloads deterministically, and provide enough telemetry to explain memory use during startup, map loads, gameplay, demo loops, and LAN hosting.

A build that requires 128 MiB hardware has not met the baseline.

## Core Policy

The system must never treat the full physical 64 MiB as application memory. After video/pbkit initialization it queries kernel memory statistics and derives a runtime renderer allowance from observed free pages.

The retail profile applies:

```text
reserved outside renderer = 4 MiB emergency/safety + 28 MiB non-renderer

if measured available memory <= reserved outside renderer:
    candidate renderer allowance = 0
else:
    candidate renderer allowance = measured available memory - reserved outside renderer

renderer allowance = min(candidate renderer allowance, 18 MiB)
renderer mandatory minimum = 8 MiB
```

All budget arithmetic uses checked/saturating integer operations. A subtraction can never wrap into a larger allowance.

The 28 MiB non-renderer reserve protects the engine/client/listen-server, game VMs, collision/world CPU structures, later audio, network queues, loading work, stacks, and SDK/runtime allocations. It is a safety partition, not a claim that those subsystems will permanently consume exactly 28 MiB.

If the computed renderer allowance is below 8 MiB, native renderer initialization fails before partial content loading. The 8 MiB floor is an initialization safety floor, not a statement that a complete Nexuiz map will fit inside 8 MiB of renderer-owned memory.

`DP_XBOX_CAP_RENDERER` remains a runtime-evidence bit and is not changed by this design.

## Architecture

Use a hybrid memory model:

1. **Kernel/system memory snapshots** for physical-memory truth.
2. **One shared contiguous GPU arena** for long-lived GPU-visible textures and static geometry.
3. **Small bounded dynamic frame rings** for transient vertex/index/constant data.
4. **A resettable scratch arena** for uploads, conversion, decompression and temporary renderer work.
5. **A tagged allocation ledger** spanning renderer and important engine allocations.
6. **An emergency diagnostics buffer** allocated before large content work so OOM reporting itself does not require allocation.

Do not create hard independent heaps for textures, world geometry, and models. Their long-lived GPU allocations share the same arena so unused capacity can move between categories.

## Source Layout

```text
xbox/platform/memory.h
xbox/platform/memory.c
    MmQueryStatistics snapshots, available-page conversion,
    global safety reserve, emergency-report storage, system summaries.

r_xbox_memory.h
r_xbox_memory.c
    Shared contiguous GPU arena, free-list allocator, coalescing,
    dynamic frame rings, scratch arena, renderer-category ledger.

r_xbox_internal.h
    Retail memory ceilings, category IDs, minimum renderer budget,
    compile-time alignment/capacity checks.

r_xbox_stats.h
r_xbox_stats.c
    Current/peak bytes, failures, largest requests, eviction counts,
    arena fragmentation, map/frame/loop watermarks.

vid_xbox.c
    Memory snapshots before and after pbkit/video initialization,
    renderer-budget derivation, refusal of unsafe startup.

zone.c
    Xbox allocation tagging hooks for important engine allocations,
    without replacing the entire DarkPlaces pool API.
```

## System Memory Measurement

Use nxdk's `MmQueryStatistics` and `MM_STATISTICS.AvailablePages` as the authoritative runtime physical-memory snapshot where available.

Required snapshots:

- process entry;
- after SDL/runtime initialization;
- after video mode selection;
- after `pb_init`;
- after renderer arena/rings allocation;
- after `Host_Init`;
- before and after map load;
- after old-map purge during transition;
- start/end of demo loops;
- before shutdown.

Each snapshot stores at least total physical pages, available pages, committed pages where reported, and derived bytes.

A failure to query statistics is fatal in retail-memory mode. Development builds may allow an explicit diagnostic override, but the default 64 MiB profile must not continue with an unknown physical-memory envelope.

## Emergency Reserve

Reserve 4 MiB globally by policy and allocate a small fixed emergency report buffer early.

Emergency report buffer:

```text
16 KiB fixed allocation
lifetime: process
purpose: OOM/fatal summaries only
```

The report path must avoid heap allocation, dynamic formatting buffers, texture creation, and filesystem allocations after an OOM is detected.

## Renderer Budget

The renderer hard ceiling is 18 MiB under the retail profile, but actual permitted bytes may be lower based on runtime free memory. Native initialization requires at least 8 MiB of renderer allowance after the global and non-renderer reserves are preserved.

The following are initial retail targets, not unconditional reservations:

| Renderer category | Initial target |
|---|---:|
| Dynamic vertex ring | 768 KiB |
| Dynamic index ring | 256 KiB |
| Program/constants staging | 128 KiB |
| Upload/decode scratch | 768 KiB |
| Renderer metadata | 384 KiB |
| Shared static GPU arena | Remaining renderer allowance |

At the 8 MiB minimum, the fixed initial targets above consume 2.25 MiB, leaving approximately 5.75 MiB for the shared static GPU arena before small allocator bookkeeping costs. A real map can still be rejected if its resources exceed the measured allowance.

The renderer may choose smaller rings when the measured allowance is low. Larger ring sizes are permitted only when an explicit higher-memory profile or measured budget allows them.

The earlier 1.5 MiB/512 KiB/256 KiB ring values become maxima, not automatic allocations.

## Shared GPU Arena

Allocate one contiguous GPU-visible region early, after pbkit/video initialization and budget calculation.

The arena serves:

- textures;
- lightmaps;
- static world vertex/index buffers;
- static model buffers;
- other long-lived GPU-visible resources explicitly approved by the renderer.

Allocator requirements:

- address-sorted free list;
- best-fit allocation;
- alignment-aware splitting;
- immediate adjacent-block coalescing on free;
- per-allocation category, lifetime and resource-name metadata;
- largest-free-block query;
- total free bytes query;
- allocation/failure counters;
- no per-frame allocation from the static arena;
- deterministic allocation order for deterministic content inputs.

Fragmentation is reported separately from total free bytes.

An allocation may fail even when total free bytes exceed the request if no aligned contiguous block is large enough. The OOM report must distinguish this case.

## Arena Pressure Policy

Static arena pressure levels:

```text
< 80% used   normal
>= 80% used  warning/high-water marker
>= 90% used  purge eligible cached resources before new growth
100% / no suitable block  deterministic allocation failure
```

Purging is allowed only for resources marked cacheable and currently unreferenced.

Fixed-quality benchmark mode must not silently alter quality to fit memory.

## Dynamic Frame Rings

Dynamic vertex, index and constant data use bounded rings with frame/fence ownership.

Initial retail sizes:

```text
vertex ring     768 KiB
index ring      256 KiB
constant ring   128 KiB
frames in flight: 3
```

Rules:

- allocate rings once during renderer initialization;
- no malloc/free during normal frame submission;
- wrap only after the owning frame is retired;
- if full, wait for the oldest owned frame rather than growing the ring;
- count stalls and peak occupancy;
- reject a single request larger than ring capacity;
- preserve 16-byte alignment for GPU-facing slices;
- never grow automatically under the retail profile.

## Scratch Arena

Use a resettable linear scratch arena for renderer-transient work.

Initial retail size: 768 KiB.

Uses include:

- texture format conversion;
- one mip-level generation/conversion at a time;
- index conversion/splitting;
- bounded upload staging;
- temporary renderer sorting/batch work where no smaller stack buffer is appropriate.

Scratch rules:

- linear/bump allocation;
- reset at explicit phase boundaries;
- no general-purpose free list;
- nested scopes use saved offsets;
- requests exceeding capacity fail immediately with stage/resource context;
- large desktop-style full-source + converted-copy + upload-copy pipelines are prohibited.

## Texture Memory Policy

Textures and lightmaps share the static GPU arena with geometry.

Texture policy:

1. Prefer prepared DXT content when quality and format support permit.
2. Prefer offline mip generation.
3. Cap dimensions by the selected retail profile.
4. Upload one bounded mip/chunk at a time.
5. Release decoded CPU image data immediately after successful upload unless the resource is explicitly dynamic.
6. Do not retain duplicate swizzled and linear copies after ownership transfers.
7. Track full mip-chain bytes, not only top-level dimensions.
8. Mark purgeable cache textures explicitly; gameplay-critical currently referenced resources are not purge candidates.

On allocation pressure:

1. release transient decoded/staging memory;
2. purge unreferenced transient textures;
3. purge eligible LRU texture cache entries;
4. retry once;
5. fail the resource/map load with `XBOX_RENDERER_OOM` if still over budget.

When automatic quality adjustment is OFF, the renderer must not silently discard high-resolution mip levels or reduce texture quality to make the scene fit.

When the user explicitly enables adaptive quality, a documented mip/precision policy may reduce future allocations, but the benchmark workload identity must record that adaptive behavior.

## Static Geometry Policy

World and model geometry shares the static GPU arena.

Rules:

- upload immutable world batches once per map;
- prefer 16-bit indices and compact vertex layouts;
- avoid duplicating CPU and GPU copies when the CPU copy is no longer required by collision/animation/streaming logic;
- keep collision structures in engine memory, not the GPU arena;
- map-scoped GPU allocations carry a map lifetime tag and are released together during transition;
- model cache resources may be LRU-purgeable only when no live entity/resource reference requires them.

## Map Transition Policy

Map transitions must avoid old-map/new-map overlap as much as engine correctness allows.

Required sequence:

```text
stop new scene submissions
wait for owned GPU frames
release map-scoped GPU allocations
purge map-scoped renderer caches
reset scratch arena
record post-purge memory watermark
load next BSP/game data
upload bounded resources incrementally
release decode/transient buffers immediately
record post-load peak
resume scene submission
```

If gameplay/network semantics require some state to survive a transition, that state must be separately tagged and its retained bytes reported.

The transition may not depend on having enough memory to hold two full maps simultaneously.

## Allocation Categories

Every tracked allocation uses one stable category:

```text
video-pbkit
render-target
gpu-arena
dynamic-vertex
dynamic-index
constants
texture
lightmap
world-buffer
model-buffer
upload-scratch
renderer-metadata
engine-core
vm-gamecode
collision
audio
network
temporary-load
emergency
```

Renderer suballocations record both arena ownership and logical category.

## Ledger and Telemetry

For each category track:

- current bytes;
- peak bytes;
- allocation count;
- free count;
- failure count;
- largest successful allocation;
- largest failed request;
- eviction/purge count where applicable.

Global renderer metrics:

- arena capacity;
- arena used/free;
- largest free block;
- external fragmentation estimate;
- ring current/peak occupancy;
- scratch current/peak occupancy;
- available physical pages at checkpoints;
- map-load high water;
- frame high water;
- demo-loop start/end watermarks.

The existing `r_xbox_stats_t` remains frame-oriented. Long-lived memory telemetry gets a separate persistent structure so `R_Xbox_StatsBeginFrame()` cannot erase lifetime peaks.

## DarkPlaces Allocator Integration

Do not replace the complete DarkPlaces mempool API.

Instead, add Xbox-only allocation tags around significant low-level allocations and expose current/peak pool totals from the existing allocator where practical.

Required engine-level visibility:

- total mempool current/peak bytes;
- largest allocations;
- VM/gamecode memory;
- model/BSP CPU-side memory;
- collision memory;
- transient loading pools;
- allocation failure context.

The renderer ledger and engine mempool totals must be reconcilable against kernel available-memory changes within a documented untracked-runtime margin.

## OOM Handling

OOM is a controlled failure state, not a quality lottery or a crash-and-continue condition.

A fixed-size OOM record contains:

```text
stage
subsystem/category
resource name
requested bytes
alignment
arena capacity
arena used
arena free
largest free block
renderer allowance
system available pages
current map/demo identifier
frame number
category current/peak bytes
```

OOM handling order:

1. stop creating the affected resource;
2. release any partially created allocation owned by the failing operation;
3. perform only the one documented purge/retry when applicable;
4. emit the fixed-memory report;
5. abort the resource/map load or renderer initialization cleanly;
6. preserve kernel/debug/fatal output;
7. never continue with incomplete GPU resource ownership.

## Renderer Initialization Integration

`vid_xbox.c` / `R_Xbox_Init()` performs memory setup in this order:

```text
query entry/platform memory
select video mode
pb_init
query post-pbkit memory
reserve emergency policy/headroom
compute renderer allowance with checked/saturating arithmetic
require at least 8 MiB allowance
allocate shared GPU arena
allocate dynamic rings
allocate scratch arena
initialize renderer metadata/default resources
query post-renderer memory
continue renderer initialization
```

If arena/rings/scratch cannot be allocated while preserving the required reserve, initialization returns failure.

## Benchmark Integrity

Fixed-quality benchmark mode requires stable memory behavior.

A scored run records:

- renderer allowance;
- static-arena capacity;
- ring sizes;
- texture-quality/adaptive setting;
- initial and peak memory snapshots;
- first-loop and final-loop watermarks;
- eviction count;
- allocation failures.

A run that changes quality or evicts workload-critical resources adaptively is not directly comparable with a fixed-quality run unless the profile explicitly identifies that behavior.

## Development Profiles

Support three memory profiles:

1. **retail64** — mandatory release profile; strict 64 MiB envelope.
2. **dev128** — permits larger allocations on upgraded hardware but still reports retail64 violations separately.
3. **xemu64** — development/emulator profile that enforces retail64 software ceilings even if the emulator exposes more memory.

128 MiB mode must never silently change the default acceptance target.

## Failure and Safety Requirements

- Never plan to consume every reported free byte.
- Never grow dynamic rings automatically on retail64.
- Never perform per-frame static-arena allocation.
- Never hide fragmentation by reporting only total free bytes.
- Never invoke a large allocating diagnostic path after OOM.
- Never silently reduce fixed-quality benchmark workload to fit memory.
- Never retain duplicate decoded/upload/GPU texture copies beyond the required ownership transition.
- Never require old and new maps to coexist fully during a transition.

## Implementation Order

This memory work must precede further renderer expansion:

1. Kernel/system memory snapshots and emergency report storage.
2. Persistent allocation categories and ledger.
3. Shared contiguous GPU arena allocator.
4. Adaptive fixed-size ring allocation within retail maxima.
5. Scratch arena.
6. `vid_xbox.c` renderer-allowance calculation and startup refusal.
7. Renderer stats integration and memory checkpoint output.
8. Texture manager consumes arena/scratch APIs.
9. Geometry/buffer manager consumes arena/ring APIs.
10. Map-transition purge/watermark integration.
11. Later audio/network allocators register their own category usage against the same global budget model.

The next NV2A state-cache task may proceed only after items 1–7 provide the memory substrate it depends on.

## Verification Gates for Later Execution

Verification is separate from source implementation. When testing resumes, gather evidence for:

1. `MmQueryStatistics` snapshots on xemu and 64 MiB hardware.
2. Arena split/coalesce/largest-free-block behavior.
3. Ring wrap/stall behavior.
4. Scratch reset/overflow behavior.
5. Renderer refusal when preserving reserve is impossible.
6. Texture/geometry pressure and deterministic purge/retry behavior.
7. Stable post-map-purge watermark.
8. Stable repeated demo-loop memory watermark.
9. OOM report generated without secondary allocation failure.
10. dev128/xemu64 profiles still reporting retail64 violations.

No build, runtime, or memory-fit claim is implied by this design document.