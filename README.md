# DarkPlaces for the Original Xbox

This fork is preparing DarkPlaces and selected Nexuiz content for the original Xbox using the open-source [nxdk](https://github.com/XboxDev/nxdk) toolchain.

The immediate target is **not a feature-complete Nexuiz console port**. The first useful product is a deterministic, continuously looping stress world that moves through mixed workloads: large BSP spaces, dense texture sets, transparency and overdraw, particles, animated geometry, math-heavy deformation, dynamic lighting, and deliberately expensive combined scenes. It must run in xemu and on a standard 64 MB retail Xbox.

## Current status

**Planning and repository bootstrap. No Xbox XBE is expected to build yet.**

The modern DarkPlaces renderer currently exposes OpenGL 3.2 and GLES2 paths. nxdk supplies SDL2 for input/audio/2D and native NV2A graphics APIs, but it does not make the existing DarkPlaces GL renderer a drop-in Xbox renderer. The central porting task is therefore a deliberately reduced `RENDERPATH_XBOX` backend with explicit feature fallbacks.

## Start here

- [Porting entry point](PORTING.md)
- [Wiki home](wiki/Home.md)
- [Port goals and scope](wiki/Port-Goals-and-Scope.md)
- [Port design](wiki/Original-Xbox-Port-Design.md)
- [Architecture](wiki/Architecture.md)
- [Renderer strategy](wiki/Renderer-Strategy.md)
- [Roadmap](wiki/Porting-Roadmap.md)
- [Implementation plan](wiki/Implementation-Plan.md)
- [Issue map](wiki/Issue-Map.md)
- [Contribution workflow](wiki/Contribution-Workflow.md)

## Non-negotiable constraints

- Open-source nxdk toolchain only; no proprietary Xbox SDK files.
- Standard 64 MB retail hardware is the baseline. A 128 MB console may be used for diagnostics, never as the acceptance target.
- Keep the existing desktop `sdl-release` build working.
- Preserve upstream-friendly boundaries: Xbox-specific code belongs in Xbox files or narrowly scoped compile guards.
- Do not commit retail game data, BIOS files, EEPROM data, keys, or unreviewed third-party assets.
- Every performance or compatibility claim needs reproducible evidence from xemu and, when the milestone requires it, real hardware.

## Upstream

This repository is based on [DarkPlacesEngine/DarkPlaces](https://github.com/DarkPlacesEngine/DarkPlaces). DarkPlaces remains GPL-licensed; see [COPYING](COPYING) and [CREDITS.md](CREDITS.md).
