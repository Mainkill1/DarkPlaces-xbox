# Memory Budget

The original Xbox has 64 MB of unified memory shared by CPU, GPU resources, executable code, engine state, content, audio, and transient work. A port that only runs on a 128 MB upgraded console has not met the baseline.

## Option B budget revision required

The table below predates playable offline/LAN acceptance and is **not a validated allocation envelope**. Issue #13 must account for the local client plus listen server, game VMs, bots/entities, collision, network queues and SDK threads/stacks concurrently with rendering and audio. Measure actual memory available after runtime/platform initialization; do not treat the whole physical 64 MiB as free application memory.

Record offline, LAN client, LAN host and benchmark peaks separately, including map-change overlap and fragmentation. Choose player/bot limits from measurements; do not add network allocations on top of an already full table or enable 128 MiB to hide a deficit.

## Initial working budget (historical planning estimate)

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

## Audio control budget

The [Xbox audio architecture](Xbox-Audio-Architecture) assigns the historical 3 MiB audio category an explicit initial runtime-data ceiling. It includes the engine/output rings, stream read-ahead and PCM windows, codec heap, decoded-SFX cache, metadata and transition reserve. It does not permit a complete compressed music track to remain resident merely because decoding is incremental.

The 3 MiB ceiling is provisional until issue #13 measures the executable, codec static data, offline client/listen-server profiles, LAN host/client profiles and map-transition overlap together. Audio must fail or evict according to its declared policy rather than borrowing silently from texture, world or safety reserves.

## Required instrumentation

- current and peak zone/mempool use;
- largest allocations;
- texture bytes by format/mip/residency;
- world/model buffer bytes;
- frame/depth/pushbuffer sizes;
- transient load peak;
- audio engine/output/hardware buffers;
- codec current/peak allocation, decoded-SFX cache and stream windows;
- free-memory sample where nxdk exposes it;
- per-loop low-water/high-water comparison;
- allocation failure context.

## Content rules

- Prefer DXT-compressed or otherwise Xbox-ready textures when quality permits.
- Generate mipmaps offline.
- Cap texture dimensions by profile.
- Avoid keeping decoded source pixels after upload.
- Use cache eviction with deterministic accounting.
- Stream long audio from stored package members; bound decoder and read-ahead state.
- Split or stream stress zones when visibility alone cannot bound residency.
- Prove that a loop returns to a stable memory watermark.

## Failure policy

An allocation failure should produce a readable subsystem/size report and a controlled exit or fallback. It must not continue with partially initialized GPU or audio state.
