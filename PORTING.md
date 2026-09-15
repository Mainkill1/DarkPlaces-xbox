# Original Xbox Porting Entry Point

The port is organized around acceptance gates, not a single long-lived “make it compile” branch.

## First useful sequence

1. Build a tiny nxdk XBE/XISO from this repository.
2. Compile the DarkPlaces core with Xbox feature pruning and no renderer.
3. Boot into a visible console with reliable logging, timing, filesystem access, and fatal-error reporting.
4. Add `RENDERPATH_XBOX` and present a cleared frame through pbkit/NV2A.
5. Draw a textured indexed mesh, then the 2D console.
6. Load and render a small Quake 3 BSP with lightmaps.
7. Add the Nexuiz material/model/effect subset required by the selected stress world.
8. Run a deterministic looping camera path and record benchmark telemetry.
9. Hold the complete workload under the 64 MB budget on real hardware.

The detailed gates and issue order are in [wiki/Porting-Roadmap.md](wiki/Porting-Roadmap.md).

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

## Evidence expected on each port PR

- Exact nxdk revision and build command.
- Result on desktop CI, xemu, and real hardware when applicable.
- Log or screenshot proving the acceptance gate.
- Binary size and memory high-water mark once instrumentation exists.
- Known fallbacks/regressions.
- No proprietary or unlicensed content in artifacts.
