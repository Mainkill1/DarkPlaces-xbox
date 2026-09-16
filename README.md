# DarkPlaces / Nexuiz for the Original Xbox

This fork targets **a fully playable Nexuiz Classic game with offline play and
LAN hosting/joining**, using the open-source [nxdk](https://github.com/XboxDev/nxdk)
toolchain. Automatic demo playback, controller-browsable graphics settings and a
continuous mixed-world benchmark remain part of the game. The owner approved
this Option B scope on 2026-09-16; it replaces the original benchmark-only target.

## Current status

PRs #31–#34 are merged at `3e273cb6a0fd96914c809c3b505de70d309600db`.
The foundation and controller-only diagnostics build, and the owner supplied an
xemu screenshot of the foundation ready screen from source `d9ede38a`.
Autoplay, controller and graphics-menu components are in the engine source and
have host/build tests. **A playable native Xbox engine is not yet implemented.**
The native system/filesystem/renderer/audio/LAN integration and real game-content
validation are still required; merging preparation code does not change that.

`make -C xbox` still builds the foundation diagnostic, not Nexuiz. Its
`renderer=disabled` output describes that target, not an option for enabling a
hidden finished game. Keep the working diagnostic as a separate regression target.

## Release target

Offline matches/bots and the campaign/progression supplied by the pinned Classic
content; real gameplay, audio, controller-only menus, persistent settings; LAN
host, discovery and manual join; automatic demo loops and graphics options with
automatic quality OFF by default. Stock 64 MiB is the memory target, with a
homebrew-capable launch environment. Internet browsing/advertising, account
services, NAT traversal and automatic external downloads are outside Option B.

The complete map/mode inventory must be tracked. An unsupported item is a visible
blocker or explicit scope exception, not silently omitted to call a subset complete.

## Start here

- [Approved playable-game and LAN design](wiki/Playable-Game-and-LAN.md)
- [Live port epic](https://github.com/Mainkill1/DarkPlaces-xbox/issues/1)
- [Porting entry point](PORTING.md) and [build targets](wiki/Build-and-Toolchain.md)
- [Wiki home](wiki/Home.md), [architecture](wiki/Architecture.md), [feature matrix](wiki/Feature-Support-Matrix.md)
- [Roadmap](wiki/Porting-Roadmap.md), [implementation order](wiki/Implementation-Plan.md), [issue map](wiki/Issue-Map.md)

## Constraints

Use open-source components only; do not commit proprietary XDK material, BIOS,
EEPROM, keys or unreviewed content. Preserve the desktop `make sdl-release` path.
Use explicit Xbox platform/native NV2A boundaries, not assumed desktop OpenGL
compatibility. Keep 128 MiB diagnostics separate from 64 MiB acceptance. Every
compatibility/performance claim must identify its build, content and executed gate.

Canonical port documentation lives in `wiki/`. The separate GitHub Wiki is a
published copy; its initialization/publication state is independent of game builds.

## Upstream

Based on [DarkPlacesEngine/DarkPlaces](https://github.com/DarkPlacesEngine/DarkPlaces).
Preserve the license and notices in [COPYING](COPYING) and [CREDITS.md](CREDITS.md).
