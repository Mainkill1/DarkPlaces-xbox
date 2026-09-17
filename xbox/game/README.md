# Nexuiz Xbox Engine Target

This directory owns the production DarkPlaces/Nexuiz Xbox executable. It is separate from the two diagnostics:

```text
xbox/Makefile                 DarkPlaces Xbox Foundation
xbox/inputcheck/Makefile      DarkPlaces Controller Check
xbox/game/Makefile            Nexuiz Xbox engine target
```

## Current source boundary

The target now has two explicit renderer selections:

```text
XBOX_RENDERER=bootstrap       prior non-rendering engine bootstrap
XBOX_RENDERER=native          direct NV2A source path under construction
```

`bootstrap` remains the default until the complete renderer source set is present. Native mode currently contains the video/device/presentation lifecycle, but not yet state translation, mesh submission, textures, fixed NV2A programs, 2D UI, BSP rendering, model rendering, or material coverage. It is therefore not a playable build and has not been compiled or executed as part of this source delivery.

The native video source owns:

- `XVideoSetMode(640, 480, 32, REFRESH_DEFAULT)`;
- pbkit initialization and shutdown;
- actual fixed-mode metadata and `RENDERPATH_XBOX` identity;
- frame begin, back-buffer targeting, bounded GPU waits, and presentation queuing;
- optional vblank pacing through the existing `vid_vsync` control;
- controller polling and the existing attract-mode/controller takeover path;
- reverse-order cleanup after partial initialization failure.

`sys_xbox.c` no longer creates a diagnostic framebuffer before `Host_Init`; early failures use the kernel/debug channel. `cl_available` is true in the native video source because DarkPlaces checks it before calling `VID_Init`; renderer runtime readiness is tracked separately and does not imply that the remaining renderer modules exist.

## Required inputs

A normal invocation will eventually use:

```sh
make -C xbox/game \
  NXDK_DIR=/absolute/path/to/pinned/nxdk \
  CONTENT_DIR=/absolute/path/to/prepared-nexuiz \
  XBOX_RENDERER=native
```

The makefile rejects missing or mismatched prerequisites before compiling:

- the pinned nxdk revision and recursive submodules;
- an output produced by the repository content-preparation path;
- required gamecode/startup/demo content and its manifest;
- a generated source/toolchain/content identity.

The project does not generate dummy gamecode or silently package unverified content.

## Planned outputs

When the target is complete and successfully built, its intended outputs are:

```text
xbox/game/build/disc/default.xbe
xbox/game/nexuiz-xbox.iso
xbox/game/build/nexuiz-xbox.map
xbox/game/build/generated/xbox_build_identity.h
```

Their presence is not claimed by the current source-only delivery.

## Remaining graphics work

The direct NV2A plan is in:

- `docs/superpowers/specs/2026-09-16-nv2a-renderer-design.md`
- `docs/superpowers/plans/2026-09-16-nv2a-renderer-implementation.md`

The remaining graphics sequence is:

1. state cache, viewport/scissor, clear, depth/blend/cull/stencil, and render-target ownership;
2. bounded vertex/index buffers and indexed draw submission;
3. textures, conversions, swizzling, mipmaps, and residency;
4. precompiled vertex programs and register-combiner recipes;
5. deterministic material planning;
6. 2D console/menu/HUD/text;
7. BSP/lightmaps/sky/fog/alpha;
8. models, weapons, particles, sprites, beams, and decals;
9. bounded dynamic-light, DOT3, reflection, and quality tiers;
10. final source cutover from bootstrap to native.

## Non-graphics boundaries

The current engine source includes filesystem and low-level LAN transport preparation. Audio is still null, no complete offline or LAN game has been demonstrated, and no real Nexuiz package is committed. These remain separate implementation and verification gates.

## Evidence policy

Compilation, linking, XBE conversion, ISO packaging, xemu boot, frame presentation, map rendering, gameplay, LAN sessions, audio, memory fit, and hardware soak are separate claims. The source in this branch was prepared without running those gates at the owner’s request.
