# Xbox Audio Architecture

**Status:** approved design for issue [#24](https://github.com/Mainkill1/DarkPlaces-xbox/issues/24). This page defines the production direction; it is not evidence that audio is implemented or working on an Xbox.

The first playable release uses **48 kHz, 16-bit signed, two-channel stereo**. Surround output, microphone capture, voice chat, hardware DSP effects, and direct AC97 ownership are outside the first-release contract.

## Decision summary

| Area | Decision |
|---|---|
| Output backend | Pinned nxdk SDL2 Xbox audio driver |
| Hardware format | 48,000 Hz, signed 16-bit little-endian, stereo |
| Hardware cadence | 1,024 frames per SDL buffer, two nxdk buffers |
| Engine mixer | Existing DarkPlaces software mixer and spatialization |
| Mixer owner | Main engine thread |
| SDL callback owner | PCM queue consumption and silence fill only |
| Runtime output queue | 8,192 stereo frames |
| Engine render ring | 8,192 stereo frames |
| Normal queue target | 6,144 frames, approximately 128 ms |
| Music/long audio | File-backed Ogg Vorbis decode through DarkPlaces VFS |
| Vorbis dependency | Static libogg 1.3.6 + libvorbis/libvorbisfile 1.3.7 |
| Stream limit | One music stream plus one auxiliary long stream |
| Short effects | WAV or Ogg decoded into a bounded deterministic cache |
| Runtime audio-data ceiling | 3 MiB until issue #13 replaces estimates with measurements |
| Benchmark modes | audible, hardware-muted, simulated mix, and no-audio are distinct |
| Production capability bit | Remains false until xemu and retail-hardware evidence passes |

## Goals

The subsystem must provide normal playable-game audio while remaining diagnosable and bounded on a stock 64 MiB console. It must:

- preserve DarkPlaces sound events, channels, looping, attenuation, pitch, Doppler, underwater filtering, occlusion policy, music controls, and stereo spatialization;
- play menu, weapon, impact, pickup, movement, ambient, announcer, game-mode, and music assets used by the pinned Nexuiz content;
- avoid decoding, filesystem access, allocation, logging, or engine-state mutation from the SDL callback;
- keep device buffering, decoded effects, codec state, and streaming windows under declared limits;
- survive pause, map transitions, sound restart, device-init failure, fatal shutdown, and repeated unattended loops;
- expose enough counters to distinguish a renderer slowdown from an audio underrun or decode stall;
- preserve the desktop `make sdl-release` target and its existing SDL backend;
- keep audio presentation time separate from simulation and benchmark progression.

## Non-goals

The first release does not implement:

- 5.1, Dolby Digital encoding, or a custom S/PDIF path;
- audio capture, headset input, or voice chat;
- EAX-style effects or hardware mixing;
- MP3, AAC, FLAC, tracker-module, or arbitrary media-container support;
- hot-switching between unrelated output devices;
- unbounded compatibility with every sound format accepted by desktop DarkPlaces.

The pinned content inventory determines the required asset set. Unsupported assets must be rejected by preparation or reported once at runtime; they must not silently consume unbounded memory.

## Existing engine boundary

DarkPlaces already owns the high-level audio behavior:

```text
Nexuiz / QuakeC sound event
            |
channel allocation, looping, pitch and position
            |
attenuation, occlusion, Doppler and stereo spatialization
            |
DarkPlaces floating-point software mixer
            |
16-bit stereo conversion
            |
Xbox platform output backend
```

The Xbox port must link `snd_main.c`, `snd_mem.c`, `snd_mix.c`, `snd_wav.c`, and the selected Ogg path rather than replacing those behaviors with an unrelated mixer. `snd_null.c` remains an explicit diagnostic build choice only; it cannot be linked beside the production sound core because it owns the same public symbols.

The current desktop `snd_sdl.c` can either mix inside SDL's audio thread or expose its render ring directly to that thread. Neither model is used unchanged on Xbox. Filesystem-backed decoding or a long mix while holding the SDL audio-device lock could delay the callback and starve nxdk's two hardware buffers. The Xbox backend therefore separates engine mixing from callback delivery with a second single-producer/single-consumer PCM queue.

## Production data flow

```text
Main engine thread

  sound events / channel state
              |
  spatialization and Ogg/WAV fetch
              |
       S_MixToBuffer()
              |
  DarkPlaces engine render ring
       8,192 frames / 32 KiB
              |
       SndSys_Submit()
              |
  bounded SPSC output queue
       8,192 frames / 32 KiB
              |
              +-----------------------------------+
                                                  |
SDL audio thread                                  |
                                                  v
  callback reads committed frames, advances queue read index,
  writes silence for any shortage, and advances device clock
              |
  nxdk SDL Xbox backend: two 1,024-frame contiguous buffers
              |
        nxdk XAudio / MCPX AC97 DMA
              |
         analog stereo and S/PDIF stereo
```

The engine render ring is main-thread-only. The SDL callback never accesses it. `SndSys_Submit()` copies newly mixed frames from that ring into the output queue. This keeps Ogg decode, resampling, and the floating-point mixer out of the callback and prevents a long main-thread mix from holding the SDL callback lock.

## Fixed output contract

### Format

`snd_xbox.c` requests and validates exactly:

```text
frequency:       48000 Hz
sample format:   AUDIO_S16LSB
channels:        2
callback frames: 1024
bytes per frame: 4
bytes per callback buffer: 4096
```

The nxdk SDL Xbox backend currently enforces this same format and uses two contiguous buffers, for 8 KiB of hardware-buffer memory. The application still validates the obtained specification. A mismatch closes the device and marks initialization failed; runtime conversion inside SDL is not accepted for the Xbox production profile.

The backend sets the effective DarkPlaces format to the obtained fixed values, forces the standard stereo channel layout, and reports one initialization record containing the format and queue sizes.

### Buffer sizing

The initial production profile uses:

| Buffer | Frames | Bytes | Time at 48 kHz |
|---|---:|---:|---:|
| One nxdk hardware buffer | 1,024 | 4 KiB | 21.33 ms |
| Both nxdk hardware buffers | 2,048 | 8 KiB | 42.67 ms |
| DarkPlaces engine ring | 8,192 | 32 KiB | 170.67 ms |
| Xbox output queue | 8,192 | 32 KiB | 170.67 ms |
| Normal queued target | 6,144 | 24 KiB | 128.00 ms |
| Low-water threshold | 2,048 | 8 KiB | 42.67 ms |

The 6,144-frame target leaves 2,048 frames of queue headroom. It tolerates ordinary 30 FPS frame intervals and moderate render spikes without retaining the desktop backend's default half-second ring. The release default remains at this conservative value until retail-hardware evidence supports a lower target without repeated low-water or underrun events.

### Main-thread submission

The Xbox backend keeps a main-thread-only absolute `submitted_frame` value. On each `SndSys_Submit()`:

1. Discard any unsubmitted frame range that has already become older than the device clock and count it as stale audio.
2. Compute the unsubmitted interval between `submitted_frame` and `snd_renderbuffer->endframe`.
3. Read the output queue's consumer index with acquire ordering.
4. Copy only the frames that fit, handling both source-ring and destination-queue wrapping.
5. Publish the output queue's producer index with release ordering.
6. Advance `submitted_frame` only for successfully committed frames.

The callback is the sole queue consumer. The main thread is the sole queue producer. The queue capacity is a power of two, and index subtraction uses unsigned wrap-safe arithmetic. Occupancy greater than capacity is an invariant failure: the callback outputs silence and latches a diagnostic rather than reading invalid memory.

SDL's 32-bit atomic operations or equivalent acquire/release barriers are used for the producer and consumer indices. No mutex is held while DarkPlaces mixes or decodes. `SndSys_LockRenderBuffer()` and `SndSys_UnlockRenderBuffer()` become successful no-ops for the Xbox backend because the engine render ring is not shared with the callback.

### Callback contract

The SDL callback may perform only bounded integer work:

- validate that the request length is a multiple of four bytes;
- snapshot the committed queue range;
- copy at most the requested number of frames, with at most two copies for wraparound;
- publish the new consumer index;
- fill any missing tail with zero-valued signed PCM;
- in hardware-muted mode, drain normally and zero the entire destination after the copy;
- increment fixed counters and the raw consumed-frame clock;
- record integer performance-counter ticks.

It may not call the DarkPlaces mixer, filesystem, memory allocator, console, logger, command system, decoder, or fatal-error path. An invalid callback request fills silence, increments an invariant counter, and returns.

## Clock and determinism

The hardware-consumed frame count is the sound-presentation clock. It must never become the game simulation clock, camera clock, demo clock, or benchmark progression clock.

The callback owns a 32-bit raw consumed-frame counter because aligned 32-bit access is safe and cheap on the target CPU. The main thread extends successive raw snapshots into a monotonic 64-bit logical frame count using unsigned-delta arithmetic. Shared DarkPlaces sound-time and render-ring absolute indices are promoted to a wrap-safe logical type where required. A synthetic rollover test must cross the approximately 24.86-hour 32-bit boundary without replaying old PCM, reporting a false underrun, or moving channel positions backward.

The following modes have distinct timing identity:

| Mode | Events | Decode/mix | SDL device clock | Audible output | Intended use |
|---|---|---|---|---|---|
| `audible` | Yes | Yes | Yes | Yes | Play and real-time soak |
| `hardware-muted` | Yes | Yes | Yes | Silence | Measure full audio cost without sound |
| `simulated` | Yes | Yes | No; host timeline | Silence | Existing `-simsound` isolation |
| `off` | No | No | No | Silence | Bring-up or graphics-only comparison |

`hardware-muted` is not implemented by setting volumes to zero because zero-volume channels can avoid fetch/decode work. It consumes and mixes the same stream as `audible`, then zeros the final SDL buffer. `off` is clearly identified as excluding audio cost. Result files and console startup records include the selected mode.

Uncapped throughput tests must use a declared `simulated` or `off` profile. Audible and hardware-muted modes are real-time modes and cannot be used to make claims about uncapped simulation throughput.

## Startup, pause, restart, and shutdown

### Startup

1. Allocate and zero backend state and the fixed output queue.
2. Create an 8,192-frame DarkPlaces render ring.
3. Initialize only the SDL audio subsystem needed by the target.
4. Open the exact fixed device while paused.
5. Validate obtained format and callback size.
6. Reset producer, consumer, submitted, and clock-extension state.
7. Return from device initialization with playback still paused so the first engine update can mix and submit PCM.
8. On the first successful `SndSys_Submit()`, require at least the 2,048-frame low-water amount, prefer the 6,144-frame target, then unpause playback and emit one main-thread initialization record.

This priming rule prevents startup from being counted as an underrun merely because `SndSys_Init()` runs before the first normal sound update. If the engine cannot produce the low-water amount, the backend remains paused and reports the blocked reason from the main thread.

An output-device failure is diagnosable rather than a memory-unsafe partial start. The engine may continue to a visible/logged error state, but the run is invalid for playable-release acceptance and `DP_XBOX_CAP_AUDIO` remains false.

### Pause and blocking

Game pause flags continue to pause their channels through existing DarkPlaces logic. Temporary sound blocking drains already queued PCM and then emits silence. It does not pause AC97 DMA or stop the device clock unless the backend is being restarted or shut down. Keeping the device clock moving prevents a resume burst of stale data.

Map changes do not recreate the output device. They stop or retain channels according to their existing flags, close obsolete decoder instances, purge eligible level-scoped cache entries, and leave the fixed backend queue allocated.

### Sound restart

`snd_restart` retains the existing restriction against running while connected. Restart performs a full pause/close/free/reopen sequence and resets all queue and stream state. It must be safe after a partially failed initialization.

### Shutdown and fatal errors

Shutdown is idempotent and ordered:

1. Latch `stopping` so new submissions stop.
2. Pause the SDL device.
3. Close the SDL device and wait for its callback thread to terminate.
4. Close active stream decoders and VFS handles.
5. Free codec/cache resources.
6. Free the output queue and engine render ring.
7. Shut down the SDL audio subsystem if this backend acquired it.

No callback-visible storage is freed before the device is closed. Fatal shutdown uses the same bounded path and never waits on a main-thread action that the callback would need in order to exit.

## Mixer and channel behavior

The production build retains the existing `DP_SMALLMEMORY` channel limits unless measured evidence supports a deliberate change:

- 64 dynamic channels;
- existing ambient channels;
- static channels up to the current total-channel cap;
- stereo music channels through the normal mixer.

The Xbox backend sets `snd_threaded = false`, so channel mutation, spatialization, decoder calls, resampling, mixing, and channel stop/free behavior remain on the main thread. This avoids races in the existing channel and fetcher structures.

Telemetry records total voices, audible/mixed voices, static combines, and peak active voices. A future voice limit or stealing policy requires content evidence and its own reviewed change; this design does not silently lower the existing limits.

The normal user controls remain `mastervolume`, `volume`, and `bgmvolume`. The controller-reachable menu must expose those controls or route to the game's existing sound menu. Diagnostic output mode is not presented as an ordinary quality setting.

## Asset policy

### Supported first-release formats

- RIFF/WAVE PCM needed by the pinned content, mono or stereo, using sample widths already accepted by the audited DarkPlaces WAV loader;
- Ogg Vorbis, mono or stereo, for music and selected effects;
- source rates accepted by the existing DarkPlaces resampler, with output always fixed at 48 kHz.

Files with unsupported channel counts, malformed headers, excessive declared sizes, unsupported compression, or inconsistent lengths fail preparation or load. The runtime reports each failed asset once by canonical identity.

### Short effects

Short WAV and Ogg effects are fully decoded into the bounded SFX cache when their decoded PCM size is no more than 128 KiB and their package policy does not force streaming. The threshold is based on decoded bytes, not compressed file size.

Decoded entries retain:

- canonical asset identity;
- source format, sample rate, channels, and frame count;
- loop information;
- decoded byte count;
- cache class and deterministic last-use sequence;
- active pin count;
- missing/failed diagnostic latch.

### Long audio and music

Long Ogg assets are file-backed. The current desktop-style implementation that calls `FS_LoadFile()` for the complete compressed file is not used for stream-class Xbox assets.

Each stream-class SFX retains only metadata. Starting a streamed channel obtains one of two fixed stream slots:

1. **Music slot** — background track and playlist use.
2. **Auxiliary slot** — one long ambience or other content-audited long sound.

Additional concurrent long assets must be converted to bounded short assets, reclassified by the content pack, or rejected during preflight. The runtime does not allocate an unbounded third decoder. Stream-slot exhaustion is counted and reported with the asset identity.

Each slot contains:

- one independently opened `qfile_t`;
- one `OggVorbis_File` decoder;
- a 64 KiB compressed read-ahead ring;
- a PCM window of at most 4,096 frames, 16 KiB for stereo S16;
- current logical frame, source offset, loop state, and error latch;
- codec allocation accounting.

The read-ahead service performs bounded main-thread prefetch work before mixing. Normal refills are limited per frame so disc or HDD reads are distributed. An emergency synchronous refill is permitted only when the decoder cannot satisfy the current mix request; it increments an emergency-read and stall counter.

### VFS callbacks

The Xbox Ogg path uses `ov_open_callbacks()` with DarkPlaces VFS operations:

- `FS_Read` for read;
- `FS_Seek` for seek;
- `FS_Tell` for tell;
- `FS_Close` for close.

A failed `ov_open_callbacks()` leaves ownership with the caller, which closes the `qfile_t`. A successful open transfers closure to the decoder callback and `ov_clear()`.

The prepared release package stores stream-class Ogg members without ZIP deflate. Deflated PK3 seeking can require repeated decompression and is not accepted for stream-class assets. The existing content staging path already writes its generated PK3 with `ZIP_STORED`; audio preflight records and verifies this property.

Loop tags and replay-gain metadata already recognized by DarkPlaces are preserved. Loop validation covers `LOOP_START`, `LOOP_END`, `LOOP_LENGTH`, and the compatible spellings currently accepted by `snd_ogg.c`.

### Static decoder dependency

The Xbox target statically links only the decode components required by the game:

- libogg 1.3.6;
- libvorbis 1.3.7;
- libvorbisfile 1.3.7;
- no encoder, examples, command-line tools, or dynamic-library loader.

The implementation records the official source archive, SHA-256, source license, and local patch hash in an audio dependency lock file. The initial lock uses the official Xiph `.tar.xz` archives:

| Archive | SHA-256 |
|---|---|
| `libogg-1.3.6.tar.xz` | `5c8253428e181840cd20d41f3ca16557a9cc04bad4a3d04cce84808677fa1061` |
| `libvorbis-1.3.7.tar.xz` | `b33cc4934322bcbf6efcbacf49e3ca01aadbea4114ec9589d1b1e9d20f72954b` |

Dependency acquisition is an explicit host step. `make -C xbox/game` performs no hidden network download; it verifies the supplied dependency directory against the lock before compiling. Required Xiph notices are included in source and release materials.

Tremor is not linked beside libvorbis. The target CPU has floating-point support, the existing DarkPlaces code already follows the libvorbisfile API, and Tremor's principal benefit is fixed-point decoding for platforms without suitable floating point. A later replacement requires an isolated hardware comparison and must remove the previous decoder rather than carrying two production implementations.

### Preparation manifest

The content preparation output gains an audio section containing, for every selected sound:

- source path and source hash;
- WAV or Ogg format details;
- source sample rate, channel count, total frames, and decoded-byte estimate;
- loop tags and normalized loop range;
- policy: `decoded`, `music-stream`, `aux-stream`, `unsupported`, or `omitted`;
- required/optional classification;
- package compression method;
- any conversion command, tool hash, output hash, and license metadata.

Preparation fails when a required asset is unsupported, a stream-class member is deflated, declared sizes exceed policy, more than the approved stream classes are required concurrently by the pinned workload, or converted loop/channel/rate information is lost.

Offline resampling or transcoding is an optimization, not a hidden runtime fallback. When used, it is deterministic and fully represented in the manifest.

## Decoded SFX cache

The cache uses deterministic sequence-based LRU ordering rather than wall-clock timestamps. Equal use sequences are resolved by canonical asset name.

Entries may be evicted only when no active channel pins them. Eviction preference is:

1. unpinned transient entries;
2. unpinned level entries no longer referenced by the current map;
3. unpinned optional entries by LRU order;
4. unpinned persistent entries only under explicit hard-limit pressure.

Active entries, the current music metadata, and required menu sounds are not evicted while referenced. Map unload first stops obsolete channels and closes their fetchers, then purges eligible level entries.

When the hard limit cannot be met without evicting a pinned entry, loading fails cleanly. A required asset failure invalidates the content/run profile; an optional cosmetic sound may be skipped, but its identity and counter are reported once.

## Initial 3 MiB runtime-data envelope

This is a control budget, not measured proof. Issue #13 may revise category boundaries only with stock-64-MiB evidence.

| Audio runtime data | Initial hard allowance |
|---|---:|
| nxdk contiguous hardware buffers | 8 KiB |
| DarkPlaces engine render ring | 32 KiB |
| Xbox output queue | 32 KiB |
| Two compressed read-ahead rings | 128 KiB |
| Two decoded stream windows | 32 KiB |
| Codec heap across both slots | 768 KiB |
| Decoded short-SFX cache | 1,408 KiB hard; 1,024 KiB soft |
| Metadata, counters, allocator records | 128 KiB |
| Transition, fragmentation, and failure reserve | 536 KiB |
| **Total runtime audio-data ceiling** | **3,072 KiB** |

Decoder executable code and static read-only tables are also measured in the executable/static category of the global memory budget. Codec allocations are routed through tracked wrappers or an equivalent allocator-accounting boundary so the decoder cannot bypass the audio ceiling unnoticed.

The backend refuses an allocation that crosses a hard sub-limit, records the requested size and owner, releases partial state, and reports the failure from the main thread.

## Telemetry

No per-callback console output is allowed. Callback and decoder faults are latched into fixed records and drained by the main thread.

### Output counters

- callback count;
- requested frames;
- copied frames;
- silence frames;
- underrun events and underrun frames;
- stale frames skipped before submission;
- output-queue full events;
- invariant failures;
- current, minimum, maximum, and target queue occupancy;
- low-water entries and longest low-water streak;
- callback maximum integer tick duration;
- device restarts and failed initializations.

### Mixer and voice counters

- frames mixed and submitted;
- audio preparation and mix time average, p95, p99, and maximum;
- active and mixed voice peaks;
- stream-slot use and exhaustion;
- sounds stopped or skipped by explicit policy;
- source resample frame count;
- delayed or failed asset starts.

### Streaming and cache counters

- compressed bytes read;
- normal and emergency refill counts;
- VFS seek count and bytes skipped/reinflated;
- decode calls, decoded frames, and decode-time distribution;
- loop seeks and loop-boundary failures;
- codec current/peak allocation;
- decoded-cache current/peak bytes;
- cache hits, misses, insertions, and evictions;
- failed asset identities, reported once.

Every benchmark or soak summary records audio mode, format, queue configuration, dependency identity, content-audio manifest hash, and whether any underrun, emergency refill, stream exhaustion, or required-asset failure occurred.

## Diagnostic commands and fixtures

The implementation provides controller-accessible or console-callable diagnostics:

- `xbox_audio_info` — format, mode, state, queue levels, stream slots, memory, and counters;
- `xbox_audio_resetstats` — reset interval statistics without hiding lifetime failures;
- `xbox_audio_tone left|right|stereo|phase` — known tones for channel/order checks;
- `xbox_audio_stress <voices>` — bounded short-effect concurrency and spatial movement;
- `xbox_audio_streamtest <asset>` — open, play, seek, loop, stop, and reopen one audited track;
- `xbox_audio_force_underrun` — diagnostic build only, deliberately withhold submissions to prove detection and recovery.

The tone fixture verifies left/right wiring through both analog and S/PDIF stereo where available. The spatial fixture passes through the normal DarkPlaces channel and mixer path rather than writing only a backend tone.

## Build integration

The game makefile gains an explicit audio selection independent of renderer selection:

```text
XBOX_AUDIO=null   diagnostic source profile
XBOX_AUDIO=sdl    production source profile
```

`null` links `snd_null.c` only. `sdl` links the complete DarkPlaces sound core, `snd_xbox.c`, WAV/Ogg support, cache/telemetry helpers, and the pinned static Xiph decoder. The source audit rejects both backends appearing in the same link set.

The default remains `null` while the source-only branch lacks runtime evidence. It changes to `sdl` only in the acceptance slice that includes successful xemu and stock-hardware validation. `DP_XBOX_CAP_AUDIO` remains `0` for source availability and changes only with that evidence-backed production default.

Expected repository ownership:

```text
snd_xbox.c / snd_xbox.h             SDL device and queue backend
snd_main.c / snd_main.h             logical clock and shared sound integration
snd_mem.c                           decoded-cache policy hooks
snd_ogg.c                           static decoder and file-backed Xbox fetcher
xbox/audio/audio_queue.*            bounded SPSC PCM queue
xbox/audio/audio_stats.*            fixed telemetry and snapshots
xbox/audio/audio_alloc.*            codec/cache accounting boundary
xbox/game/sources.mk                mutually exclusive source sets
xbox/game/Makefile                  XBOX_AUDIO selection and static dependencies
xbox/game/profile.h                 platform capability policy
tools/xbox/audio_prepare.py         asset audit and policy manifest
```

Names may be consolidated when a helper would contain only trivial wrappers, but ownership and link exclusivity remain as specified.

## Validation ladder

### Host and desktop

1. Ring tests cover empty, partial, exact, wrapped, full, and invariant-corrupt states.
2. Producer/consumer tests run randomized schedules and prove byte-for-byte order.
3. Hardware-muted mode consumes exactly the same logical frames as audible mode.
4. Synthetic device-clock tests cross 32-bit rollover.
5. Shutdown tests close a callback-active device before freeing queue storage.
6. Ogg callback tests cover read, seek, tell, close, failed open, and repeated loop seeks through a stored PK3 fixture.
7. Tests prove a stream-class asset is not loaded through `FS_LoadFile()`.
8. Cache tests prove deterministic eviction, active pinning, hard-limit refusal, and stable map-transition memory.
9. Malformed WAV/Ogg fixtures fail without leak or repeated log spam.
10. Desktop `make sdl-release` remains green.

### nxdk compile and package

1. Static libogg/libvorbis/libvorbisfile compile with the pinned nxdk revision.
2. `XBOX_AUDIO=sdl` links one and only one `SndSys_*` owner.
3. The XBE/XISO carries dependency, content-audio, and backend identity.
4. Source and symbol audits prove no DLL loader, encoder, or desktop audio backend entered the XBE.

### xemu

1. Exact format initialization and tone/channel test.
2. Menu, weapon, movement, pickup, announcer, ambient, and music reference sequence.
3. Concurrent positional effects while a streamed track plays.
4. Loop-boundary and seek fixture.
5. Pause/resume, map unload/reload, `snd_restart`, and controlled initialization failure.
6. Deliberate underrun followed by stable recovery.
7. Offline match, LAN client, and LAN host profiles with audio enabled.
8. Repeated demo loops return cache, stream, and decoder state to stable baselines.

### Stock 64 MiB hardware

1. Analog stereo left/right test; S/PDIF stereo when test equipment is available.
2. Same reference sequence and loop test as xemu.
3. Memory reconciliation against the 3 MiB audio ceiling and global issue #13 budget.
4. At least 30 minutes of mixed gameplay with no repeated underrun.
5. Multi-hour unattended stress playback with no progressive drift, leak, callback stall, or decoder growth.
6. Fatal/restart paths exit or recover without deadlock.

## Implementation slices

The architecture is implemented in independently reviewable slices. Each slice leaves the branch buildable and updates issue #24 with evidence.

### Slice A — contracts and failing host tests

- Add the queue, clock, mode, and telemetry contracts.
- Add failing tests for order, wrap, underrun, mute, rollover, and shutdown.
- Add audio dependency lock and source/license verification tests.
- Keep the production source selection on `null`.

### Slice B — fixed SDL output and WAV path

- Add `snd_xbox.c` and the dual-ring submission path.
- Link the existing mixer and WAV loader.
- Add exact-format startup, lifecycle handling, modes, and output counters.
- Produce compile/link and xemu tone evidence.

### Slice C — file-backed Vorbis streaming

- Build the pinned static Xiph decoder.
- Replace complete-file residency for Xbox stream-class Ogg assets.
- Add two bounded stream slots, read-ahead, loop metadata, and decoder accounting.
- Extend content preparation and validate a long looped track.

### Slice D — bounded SFX cache and diagnostics

- Enforce decoded-byte thresholds, deterministic LRU, active pins, and map purge.
- Add diagnostics, interval summaries, and malformed-asset coverage.
- Reconcile the audio category with issue #13 measurements.

### Slice E — real-game and hardware acceptance

- Validate the pinned full-game sound inventory, offline play, LAN client/host, and stress route.
- Attach xemu and stock-64-MiB results.
- Switch the production default from `null` to `sdl` and set the evidence-backed capability bit.
- Leave `null`, `simulated`, and `hardware-muted` available as clearly identified diagnostic profiles.

## Acceptance criteria

Audio is complete for the first playable release only when all of the following are true:

- the production target defaults to exact 48 kHz S16 stereo through nxdk SDL2;
- every required pinned sound is supported or has an approved deterministic conversion;
- music and long assets do not retain their complete compressed files in memory;
- normal reference runs report no repeated underrun, stream exhaustion, invariant failure, or required-asset failure;
- muted and no-audio results cannot be mistaken for audible results;
- current and peak audio allocations reconcile with the stock-64-MiB memory report;
- loop, map transition, restart, fatal shutdown, offline play, LAN client, and LAN host tests pass;
- repeated and multi-hour runs show stable device clock, decoder state, cache usage, and queue behavior;
- desktop SDL remains green;
- issue #24 contains links to the implementation, evidence, supported-format documentation, and final dependency manifest.

## Rejected alternatives

### Direct XAudio production backend

nxdk's direct API currently provides the same fixed 16-bit stereo capability and explicitly positions SDL2 as the application-facing path. Reimplementing device queues, callback wake-up, and lifecycle handling would add ownership without a required output feature. Direct XAudio remains useful only as a lower-level diagnostic if SDL-specific behavior must be isolated.

### Mixing inside the SDL callback

This would place floating-point mixing, resampling, decoder work, and possibly filesystem reads on the SDL audio thread. It also makes CPU attribution and channel-state synchronization harder. The production callback is therefore a bounded queue consumer only.

### One shared ring protected during mixing

Holding the SDL device lock while DarkPlaces mixes or decodes can delay the callback long enough to drain nxdk's two hardware buffers. The separate output queue permits expensive main-thread work without blocking callback delivery.

### Loading complete Ogg files into memory

Decoding on demand does not constitute bounded streaming when the complete compressed track remains resident. File-backed VFS callbacks and fixed stream slots replace this behavior.

### Shipping multiple Vorbis decoders

Keeping libvorbis, Tremor, and another fallback increases code size, test combinations, and format ambiguity. The first implementation uses one pinned static decoder. Any replacement must provide measured evidence and remove the previous production path.
