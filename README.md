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

The port now has two game-engine implementation paths with deliberately different
roles:

- `xbox/classic/` is the integrated **first release-candidate** route. It pins a
  Nexuiz-era DarkPlaces revision, maps its historical fixed-function renderer to
  pbGL/PBKit/NV2A, and includes Xbox video/controller, SDL stereo audio and nxdk
  networking integration.
- `xbox/game/` is the modern-engine direct `RENDERPATH_XBOX` development route.
  Its lower-level native renderer is not complete yet and remains a development
  path rather than the first end-to-end package entry.

Neither source presence nor a host build is a gameplay claim. The integrated
candidate still requires a full cross-build followed by xemu and stock-64-MiB
runtime validation for rendering, audio, offline gameplay, LAN and soak.

`make -C xbox` still builds the foundation diagnostic, not Nexuiz. Keep that
working diagnostic as a separate regression target.

## First complete build entry

Engineers should start with [`xbox/release/`](xbox/release/README.md), not guess
between Xbox directories. It locks every external source revision and the complete
Nexuiz 2.5.2 archive identity in `xbox/release/release-inputs.json`.

From a clean checkout:

```sh
# Explicit network step: clone exact open-source dependencies and obtain the
# historical game archive, verifying it before use.
make -C xbox/release bootstrap

# Offline after bootstrap: verify, stage the full game data tree, compile/link,
# create default.xbe + XISO and write build/content identity manifests.
make -C xbox/release all
```

If `nexuiz-252.zip` is already available, pass `NEXUIZ_ARCHIVE=/path/to/nexuiz-252.zip`;
the same committed SHA-256 is enforced. The game archive and dependency checkouts
are local ignored inputs, not repository content and not expiring CI artifacts.

Intended successful outputs are:

```text
xbox/release/out/nexuiz-xbox.xbe
xbox/release/out/nexuiz-xbox.iso
xbox/release/out/BUILD-IDENTITY.txt
xbox/release/out/CONTENT-IDENTITY.json
xbox/release/out/SHA256SUMS
```

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

- [Canonical release-candidate build](xbox/release/README.md)
- [Approved playable-game and LAN design](wiki/Playable-Game-and-LAN.md)
- [Live port epic](https://github.com/Mainkill1/DarkPlaces-xbox/issues/1)
- [Porting entry point](PORTING.md) and [build targets](wiki/Build-and-Toolchain.md)
- [Wiki home](wiki/Home.md), [architecture](wiki/Architecture.md), [feature matrix](wiki/Feature-Support-Matrix.md)
- [Roadmap](wiki/Porting-Roadmap.md), [implementation order](wiki/Implementation-Plan.md), [issue map](wiki/Issue-Map.md)

## Constraints

Use open-source components only; do not commit proprietary XDK material, BIOS,
EEPROM, keys or unreviewed content. Preserve the desktop `make sdl-release` path.
Use explicit Xbox platform/native NV2A boundaries; the release-candidate pbGL
compatibility route is isolated from the modern direct-native renderer work.
Keep 128 MiB diagnostics separate from 64 MiB acceptance. Every compatibility
or performance claim must identify its build, content and executed gate.

Canonical port documentation lives in `wiki/`. The separate GitHub Wiki is a
published copy; its initialization/publication state is independent of game builds.

## Upstream

Based on [DarkPlacesEngine/DarkPlaces](https://github.com/DarkPlacesEngine/DarkPlaces).
Preserve the license and notices in [COPYING](COPYING) and [CREDITS.md](CREDITS.md).
