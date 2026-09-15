# Memory Budget

The original Xbox has 64 MB of unified memory shared by CPU, GPU resources, executable code, engine state, content, audio, and transient work. A port that only runs on a 128 MB upgraded console has not met the baseline.

## Initial working budget

These are planning caps, not measured truth. The allocator telemetry issue must replace estimates with high-water values.

| Category | Initial cap |
|---|---:|
| Executable, static data, stacks, core engine/QC | 12 MB |
| Frame/depth buffers, push buffers, GPU bookkeeping | 8 MB |
| World geometry, visibility, collision | 10 MB |
| Resident textures/lightmaps | 18 MB |
| Models, particles, dynamic geometry | 5 MB |
| Audio | 3 MB |
| Transient decode/loading workspace | 4 MB |
| Safety reserve / fragmentation | 4 MB |
| **Total** | **64 MB** |

The categories share physical memory; the table is a control mechanism for content and cache decisions, not a claim that each subsystem receives a separate heap.

## Required instrumentation

- current and peak zone/mempool use;
- largest allocations;
- texture bytes by format/mip/residency;
- world/model buffer bytes;
- frame/depth/pushbuffer sizes;
- transient load peak;
- audio buffers;
- free-memory sample where nxdk exposes it;
- per-loop low-water/high-water comparison;
- allocation failure context.

## Content rules

- Prefer DXT-compressed or otherwise Xbox-ready textures when quality permits.
- Generate mipmaps offline.
- Cap texture dimensions by profile.
- Avoid keeping decoded source pixels after upload.
- Use cache eviction with deterministic accounting.
- Split or stream stress zones when visibility alone cannot bound residency.
- Prove that a loop returns to a stable memory watermark.

## Failure policy

An allocation failure should produce a readable subsystem/size report and a controlled exit or fallback. It must not continue with partially initialized GPU state.
