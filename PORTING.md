# Original Xbox Porting Entry Point

The port is organized around acceptance gates, not a single long-lived “make it compile” branch.

The live execution source of truth is the [master port epic](https://github.com/Mainkill1/DarkPlaces-xbox/issues/1). Its child issues contain dependencies, deliverables, evidence requirements, and completion criteria. The `wiki/` directory records durable architecture and policy.

## Approved scope

[Option B](wiki/Playable-Game-and-LAN.md) is the release contract: fully playable Nexuiz Classic offline plus LAN, with autoplay/benchmarking retained. The existing diagnostic boot does not satisfy engine/game acceptance. Keep local/listen-server code, required gamecode, audio and persistence in the production target; Internet services remain excluded.

## Which build path to use

A future engineer should not invent another target or guess from directory names:

```text
xbox/Makefile       foundation/toolchain diagnostic
xbox/inputcheck/    controller diagnostic
xbox/game/          modern direct RENDERPATH_XBOX development path
xbox/classic/       integrated Nexuiz-era DarkPlaces + pbGL/NV2A candidate
xbox/release/       canonical first end-to-end build/package entry
```

For the first complete game integration attempt, use:

```sh
make -C xbox/release bootstrap
make -C xbox/release all
```

`bootstrap` performs the explicit network acquisition step. It obtains exact pinned open-source dependencies and the historical Nexuiz 2.5.2 archive, verifies immutable identities, and leaves them in ignored local `deps/`. The remaining gates do not hide network downloads.

The integrated `xbox/classic` route is intentionally used to reach a complete XBE sooner because the Nexuiz-era engine still owns the fixed-function renderer that pbGL can map to NV2A. `xbox/game` remains the lower-level direct-native renderer path. Runtime evidence decides which compatibility pieces must be replaced; packaging/content/dependency ownership stays in `xbox/release` either way.

## First useful sequence

1. Verify the committed release lock and acquire exact dependencies/content through `xbox/release`.
2. Preserve the known foundation and input diagnostics as independent regression gates.
3. Compile/link/package the integrated game candidate without dropping client/server/gamecode/audio/network services to make the link easier.
4. Boot the exact packaged identity and reach normal DarkPlaces host/filesystem initialization.
5. Measure/enforce the standard 64 MB memory profile before broad content tuning.
6. Establish menu/2D, world/BSP, models and effects on pbGL/NV2A; replace compatibility gaps with explicit native implementation where required.
7. Validate zero-action autoplay and fresh-button takeover.
8. Complete offline games with bots/campaign, bounded stereo audio, controller menus and persistence (#35/#24).
9. Host and join LAN games, including map rotation, disconnect and rejoin (#36).
10. Retain the continuous benchmark with fixed/adaptive settings and distinct real-time/throughput behavior.
11. Validate complete games, content coverage, LAN and benchmark loops under the measured 64 MiB budget on xemu and hardware.
12. Continue direct `RENDERPATH_XBOX` migration where it measurably improves correctness, memory use or performance without forking release packaging.

The phase gates are in [wiki/Porting-Roadmap.md](wiki/Porting-Roadmap.md), and the live issue-to-phase mapping is in [wiki/Issue-Map.md](wiki/Issue-Map.md).

## Platform file boundaries

The repository currently separates the integration and direct-native backends:

```text
xbox/release/                 dependency lock, content staging, release packaging
xbox/classic/sys_xbox.c       Nexuiz-era process/timing/static dependency boundary
xbox/classic/vid_xbox.c       pbGL/PBKit video + controller lifecycle
xbox/classic/gl_compat.c      historical GL1.x -> pbGL compatibility resolver
xbox/classic/snd_xbox.c       initial Xbox SDL stereo backend
xbox/classic/net_xbox.c       nxdk network integration anchor

sys_xbox.c / vid_xbox.c       modern direct-native platform work
r_xbox*.c                     direct RENDERPATH_XBOX backend modules
```

The classic compatibility route is not permission to scatter desktop OpenGL assumptions through new shared code. Keep compatibility localized and move unsupported/expensive behavior behind explicit Xbox boundaries.

## Build policy

Do not silently treat nxdk as `WIN32`. nxdk exposes useful Windows-like APIs, but the Xbox platform has different filesystem, DLL, memory, graphics, and process semantics. Define and use an explicit `DP_PLATFORM_XBOX` build symbol.

Do not add pretend-success targets. A game build either produces the expected candidate files or fails with a direct prerequisite/compiler/link/package error.

The release-input lock is `xbox/release/release-inputs.json`. Moving branches, unverified mirrors and expiring CI artifacts are not acceptable dependencies. The complete Nexuiz archive remains external to Git and is verified before extraction.

## Documentation policy

Canonical port documentation lives under `wiki/`. Some issue text created during initial planning names future `docs/xbox-port/...` files; implement those deliverables as the corresponding `wiki/` page, or add a new wiki page and link it from `wiki/Home.md`. Do not create a competing documentation tree.

## Evidence expected on each port PR

- Exact DarkPlaces, nxdk, pbGL/native renderer, Ogg/Vorbis and content revisions/hashes that apply.
- Result on desktop CI, cross-build CI, xemu, and real hardware when required by the issue.
- Log, screenshot, capture, counter report, or artifact proving the acceptance gate.
- Binary size and memory high-water mark once instrumentation exists.
- Workload/profile identity for performance results.
- Known fallbacks, caps, regressions, and unsupported paths.
- No proprietary or unlicensed content in published artifacts.
