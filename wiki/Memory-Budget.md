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

## Classic candidate static-image gate

The first stock-memory boot trace reached `GL_Init complete` and then failed its
first texture-management allocation. Inspection found that the linked PE image
reserved 35,090,432 bytes, dominated by desktop-scale fixed arrays.

The canonical classic build now materializes Xbox-only limits without modifying
the immutable engine checkout:

| Limit | Pinned engine | Xbox classic candidate |
|---|---:|---:|
| Client/server entities | 32,768 | 8,192 |
| Models | 8,192 | 2,048 |
| Sounds | 4,096 | 2,048 |
| Server-browser entries | 2,048 | 256 |

The resulting PE `SizeOfImage` is 21,528,576 bytes, reclaiming 13,561,856 bytes
before runtime heap and GPU allocation. `xbox/release` rejects a classic PE over
24 MiB. This is a static-footprint gate, not proof of the complete 64 MiB runtime
gate; map loading, offline play, LAN hosting, transitions, and soak still require
measured high-water evidence.

## Classic runtime profile selection

The next stock-memory trace advanced through the first completed framebuffer
swap, stereo-audio initialization, and Nexuiz gamecode loading. It then failed
while allocating a decoded sound buffer in `snd_mem.c:90`. This is later than
the prior texture-management failure, but it is still an allocation failure
before a complete map/gameplay route.

The classic candidate now queries `MmQueryStatistics` before `Host_Main` and
uses one XBE for three runtime profiles:

| Selection | Condition | Policy |
|---|---|---|
| `retail64` | automatic below 112 MiB, or explicit | Stock-memory ceilings |
| `dev128` | automatic at or above 112 MiB, or a safe explicit request | Larger system heap; diagnostic only |
| `xemu64` | explicit | Retail ceilings even when xemu exposes more memory |

The gap below 112 MiB deliberately selects `retail64`; the code does not infer
that an unusual intermediate capacity is safe for `dev128`. To override the
automatic choice, place exactly one of `retail64`, `dev128`, or `xemu64` in:

```text
E:\UDATA\Nexuiz\memory-profile.txt
```

An invalid value returns to automatic selection. A `dev128` request below the
112 MiB threshold is rejected and safely falls back to `retail64`. The durable
boot trace records the requested/selected profile plus total and available
physical memory.

The structural limits in the preceding table stay identical for all profiles;
they determine static array and executable size. After saved configuration is
loaded and before autoplay begins, `retail64` and `xemu64` only tighten values
that exceed their ceilings:

| Runtime control | Retail/xemu64 ceiling |
|---|---:|
| `gl_max_size` | 1024 maximum |
| `gl_picmip` | 1 minimum |
| `r_precachetextures` | 0 maximum |
| `snd_precache` | 0 maximum |
| `snd_streaming` | 1 minimum |

More conservative saved graphics choices are preserved. `dev128` does not
replace user choices and can benefit from its larger normal heap, but the
current classic renderer still lacks the complete arena/cache/eviction ledger
needed to quantify retail-equivalent violations. A `dev128` run is therefore
reported as diagnostic-only, never as 64 MiB acceptance. The trace reports
before/after values and a `retail64_ceiling_violations` count for the five
controls above; that count is not a substitute for the still-missing complete
runtime allocation ledger.

The 2026-09-18 follow-up 64 MiB trace confirmed that `retail64` was selected
and applied before autoplay (`snd_precache 1->0`, `r_precachetextures 1->0`).
The run reached the same visible point but did not repeat the earlier sound
allocation failure. Instead, packed-file inflation returned short and the
legacy loader passed the partially filled buffer into the TGA decoder, which
then failed at `image.c:435`. The Xbox materialized filesystem source now
rejects and frees incomplete reads rather than treating them as valid assets,
and records the asset path, expected/actual byte counts, zlib result, and
current available physical page count. Both staged PK3 files also pass complete
`unzip -tq` validation, isolating the failure to the runtime read/decompression
boundary rather than the packaged payload. This is a source/build gate until
another xemu run shows the next runtime boundary.

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
