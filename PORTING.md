# Original Xbox Porting Entry Point

The port is organized around acceptance gates, not a single long-lived “make it compile” branch.

The live execution source of truth is the [master port epic](https://github.com/Mainkill1/DarkPlaces-xbox/issues/1). Its child issues contain dependencies, deliverables, evidence requirements, and completion criteria. The `wiki/` directory records durable architecture and policy.

## First useful sequence

1. Lock the MVP, compatibility promise, reference workload, source/dependency audit, content policy, and renderer baseline.
2. Pin nxdk and build a tiny repository-owned XBE/XISO.
3. Compile the DarkPlaces core with Xbox feature pruning and no production renderer.
4. Boot into a visible console with reliable logging, timing, filesystem access, and fatal-error reporting.
5. Enforce the standard 64 MB memory profile before full map and renderer work.
6. Add `RENDERPATH_XBOX` and present a cleared frame through pbkit/NV2A.
7. Draw a textured indexed mesh, then the 2D console.
8. Load and render a small BSP with lightmaps.
9. Add the Nexuiz material/model/effect subset required by the selected stress world.
10. Run one deterministic looping camera path and record machine-readable telemetry.
11. Hold the complete workload under the 64 MB budget on real hardware.

The phase gates are in [wiki/Porting-Roadmap.md](wiki/Porting-Roadmap.md), and the live issue-to-phase mapping is in [wiki/Issue-Map.md](wiki/Issue-Map.md).

## Planned Xbox file boundary

The first implementation should favor new, reviewable platform files rather than spreading Xbox conditions through the engine:

```text
xbox/
  Makefile                 nxdk-facing build entry point
  config_xbox.h            feature policy and hard platform limits
  README.md                build/layout notes
  shaders/                 NV2A vertex programs and combiner descriptions
  tools/                   host-side content conversion helpers

sys_xbox.c                 process, timing, logging, fatal error handling
vid_xbox.c                 controller events, video lifecycle, present
snd_xbox.c                 audio backend or explicit no-audio backend
thread_xbox.c              threading primitives / single-thread fallback
r_xbox.c / r_xbox_*.c      RENDERPATH_XBOX backend modules
```

Exact names may change during the renderer architecture issue, but the separation must remain.

## Build policy

Do not silently treat nxdk as `WIN32`. nxdk exposes useful Windows-like APIs, but the Xbox platform has different filesystem, DLL, memory, graphics, and process semantics. Define and use an explicit `DP_PLATFORM_XBOX` build symbol.

Do not add a pretend-success target. The first `make xbox` merge must either produce a bootable XBE/XISO or fail with a direct prerequisite/error message.

The production renderer is not “SDL on Xbox.” SDL2 may be selected for bounded input or audio work, but NV2A rendering requires the architecture chosen and proven by [issue #3](https://github.com/Mainkill1/DarkPlaces-xbox/issues/3).

## Documentation policy

Canonical port documentation lives under `wiki/`. Some issue text created during initial planning names future `docs/xbox-port/...` files; implement those deliverables as the corresponding `wiki/` page, or add a new wiki page and link it from `wiki/Home.md`. Do not create a competing documentation tree.

## Evidence expected on each port PR

- Exact DarkPlaces, nxdk, content, converter, xemu, and hardware revisions that apply.
- Result on desktop CI, cross-build CI, xemu, and real hardware when required by the issue.
- Log, screenshot, capture, counter report, or artifact proving the acceptance gate.
- Binary size and memory high-water mark once instrumentation exists.
- Workload/profile identity for performance results.
- Known fallbacks, caps, regressions, and unsupported paths.
- No proprietary or unlicensed content in artifacts.
