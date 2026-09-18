# Nexuiz Xbox release-candidate build

This directory is the **single first-build entry point** for producing the complete playable-game XBE/XISO candidate. It exists so an engineer does not have to guess between the repository's diagnostic targets and renderer-development targets.

## Which target is which?

| Path | Purpose |
|---|---|
| `xbox/Makefile` | nxdk/foundation diagnostic only |
| `xbox/inputcheck/` | controller diagnostic only |
| `xbox/game/` | modern-engine direct `RENDERPATH_XBOX` development path; native renderer still incomplete |
| `xbox/classic/` | integrated Nexuiz-era DarkPlaces + pbGL/NV2A + Xbox platform/audio/network target |
| **`xbox/release/`** | **canonical first end-to-end release-candidate wrapper around `xbox/classic`** |

Using `xbox/classic` for the first complete build does not declare the direct-native renderer work abandoned. It gives the project one complete integration route to boot and profile while the lower-level native backend continues to mature.

## Inputs

`release-inputs.json` locks every external source and the complete Nexuiz 2.5.2 archive. The build does not accept branch names, moving tags, or an unverified game archive.

Current source inputs:

```text
nxdk       29638d0b001f179b73c3513489af10ddc2986216
DarkPlaces 7349e20fba3c2b469616505907109863e8cb4a9e
pbGL       017ab17c4530bf3e2ad446a50de9b18ea6011548
libogg     be05b13e98b048f0b5a0f5fa8ce514d56db5f822  (1.3.6)
libvorbis  0657aee69dec8508a0011f47f3b69d7538e9d262  (1.3.7)
```

Nexuiz content:

```text
file:   nexuiz-252.zip
size:   931253731 bytes
SHA256: a5e27ebcc9775c4a490d0d3536c32e4a8f8f96b038c0b6a78d1823c37a962000
MD5:    d750bc328e58df8492f8d88bdcf818cb
```

The archive is **not committed to this repository**. `make content` retrieves the historical release from the official SourceForge project page into ignored local `deps/`, or you can provide an existing archive with `NEXUIZ_ARCHIVE=/absolute/path/nexuiz-252.zip`. Either path must match the locked byte count, SHA-256 and historical MD5 before extraction.

## Host prerequisites

A Debian/Ubuntu-style build host should have at least:

```sh
sudo apt-get install build-essential clang llvm lld cmake flex bison pkgconf git python3 curl
```

nxdk's own documented host requirements still apply. Do not use proprietary Microsoft XDK tools or headers.

## Clean-checkout flow

### 1. Acquire immutable inputs

This is the only phase that intentionally uses the network:

```sh
make -C xbox/release bootstrap
```

It creates ignored checkouts under `deps/`, checks out the exact commits from `release-inputs.json`, initializes nxdk submodules, downloads the official game archive to a temporary file, verifies its size/hashes, and only then renames it into place.

If you already have the archive:

```sh
make -C xbox/release deps
make -C xbox/release preflight NEXUIZ_ARCHIVE=/absolute/path/nexuiz-252.zip
```

### 2. Build the complete candidate

After inputs exist, the complete build is offline:

```sh
make -C xbox/release all
```

Or run gates independently:

```sh
make -C xbox/release preflight
make -C xbox/release stage
make -C xbox/release engine
make -C xbox/release xbe
make -C xbox/release verify-tree
make -C xbox/release xiso
make -C xbox/release verify-xiso
make -C xbox/release package
```

`engine`, XBE generation and packaging never download dependencies or game content.

## Packaging guarantees

The release wrapper deliberately does **not** delegate XISO freshness to nxdk's generic `all` dependency graph. The staged game tree can change while `default.xbe` remains unchanged, so the wrapper always removes and recreates the XISO after staging.

Before image creation, `tools/xbox/verify_release_tree.py` reconciles:

- a plausible `default.xbe` with `XBEH` magic;
- `BUILD-IDENTITY.txt` against `CONTENT-IDENTITY.json`;
- every staged `data/` file against its recorded size and SHA-256;
- exact staged data membership, including Xbox defaults and original game data;
- no symlink/case-collision surprises;
- at least one actual Nexuiz PK3.

After image creation, `tools/xbox/verify_xiso.py` parses the XDVDFS directory tree directly and requires the image file list, sizes and packaged payload hashes to match the staging tree. `default.xbe` is checked by size/magic rather than byte-for-byte because `extract-xiso` may apply its standard media-enable patch during image creation.

## Intended outputs

A successful package gate must leave:

```text
xbox/release/out/
  nexuiz-xbox.xbe
  nexuiz-xbox.iso
  BUILD-IDENTITY.txt
  CONTENT-IDENTITY.json
  SHA256SUMS
```

The XISO is staged from the **complete Nexuiz 2.5.2 `data/` tree**, not a benchmark-only subset. The stager adds `xbox-defaults.cfg` and appends `exec xbox-defaults.cfg` to an existing `autoexec.cfg` instead of replacing the game's original startup configuration.

The Xbox defaults preserve:

- controller movement/look and combat bindings;
- automatic quality **OFF**;
- uncapped benchmark-friendly presentation settings;
- zero-action demo startup and controller takeover/restart behavior.

They also invoke `xbox_apply_memory_profile` after normal saved configuration
has loaded and before autoplay begins. The XBE selects `retail64` below 112 MiB
of detected physical memory and `dev128` at or above 112 MiB. `dev128` is a
diagnostic profile and does not count as stock-memory acceptance.

For controlled testing, create
`E:\UDATA\Nexuiz\memory-profile.txt` containing exactly `retail64`, `dev128`,
or `xemu64`. `xemu64` applies retail ceilings even with expanded emulator
memory. An unsafe `dev128` request on a smaller-memory system falls back to
`retail64`; invalid values return to automatic selection. The immutable engine
array limits remain conservative in every profile.

## What this does not prove

A successful host build is only the compile/link/package gate. Before describing the port as working, the produced artifacts still need explicit evidence for:

```text
XBE boot
Host_Main / filesystem initialization
menu and 2D presentation
map/BSP rendering
controller-only game setup
zero-action autoplay and takeover
stereo audio and music
complete offline match + bots/campaign
LAN host and LAN client match
map changes / reconnect
stock 64 MiB memory fit
extended xemu and hardware soak
```

The first full build is expected to expose additional source/compiler/runtime issues. Fix those against this one reproducible input identity rather than creating another build route.
