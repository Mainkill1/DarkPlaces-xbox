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

`CONTENT_PROFILE=stock64` is the default final-acceptance content policy.
For the current 128 MiB playable milestone, explicitly build with:

```sh
make -C xbox/release all CONTENT_PROFILE=dev128
```

Use an emulator configured for 128 MiB with that image. The staged startup
configuration checks its content profile against the detected runtime profile
before autoplay and records a fatal mismatch in the boot trace.
The release wrapper also clears the pinned `cxbe` tool's default 64 MiB XBE
runtime-limit bit for `dev128`; it leaves that bit set for `stock64`. The
pre-XISO tree verifier checks the bit against the content identity, because
emulator RAM settings alone do not make the extra memory visible to the game.
Before evaluating gameplay, confirm `Xbox memory profile=dev128 ... total=128 MiB`
in `E:/UDATA/Nexuiz/boot-trace.txt`. If it still reports `total=64 MiB`, the
firmware/kernel is not exposing expanded memory to this XBE; the content
profile guard stops before autoplay. Changing xemu's memory setting alone has
not been sufficient in this workspace.

After the first swap, the trace records `Xbox presented frame=...` with
`world_loaded`, `available_pages`, `low_water_pages`, and whether sampled
physical headroom is at least 20 MiB. It repeats every 60 presented frames.
These are sampled free pages, not a complete allocation ledger or proof that
the entire offline/LAN route is stable.

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

After image creation, `tools/xbox/verify_xiso.py` parses the XDVDFS directory tree directly and requires the image file list, sizes and packaged payload bytes to match the staging tree. For `default.xbe`, the verifier permits only the pinned `extract-xiso` media-enable byte substitution and compares every other byte.

## Intended outputs

A successful package gate must leave:

```text
xbox/release/out/<stock64-or-dev128>/
  nexuiz-xbox.xbe
  nexuiz-xbox.iso
  BUILD-IDENTITY.txt
  CONTENT-IDENTITY.json
  SHA256SUMS
```

The XISO is staged from the **complete Nexuiz 2.5.2 `data/` tree**, not a benchmark-only subset. The stager adds `xbox-defaults.cfg` and appends `exec xbox-defaults.cfg` to an existing `autoexec.cfg` instead of replacing the game's original startup configuration.

Staging generates one profile-specific override pack from the verified original
PK3s. `stock64` uses `data/zzzz-xbox-lowmem.pk3` with 256 px general textures
and 64 px external lightmaps. `dev128` uses `data/zzzz-xbox-dev128.pk3` with
512 px general textures and 128 px external lightmaps. Both use deterministic
repeated box filtering and stored, uncompressed TGA entries, avoiding a runtime
DEFLATE workspace for the overrides. The original PK3 bytes are unchanged.
`CONTENT-IDENTITY.json` records the chosen profile, pack policy, asset count,
size, and SHA-256; the tree and XISO verifiers require exactly that pack.
See [Low-Memory Material Downscaling](../../wiki/Low-Memory-Material-Downscaling.md).

External Q3 lightmaps named `maps/<map>/lm_NNNN.tga` have a stricter 64x64
ceiling. The Xbox classic build validates the external set and then decodes,
converts, uploads, and frees one image at a time; it does not apply normal world
picmip to the resulting GPU textures. The separate ceiling bounds transient
and resident use while preserving the loader's required square power-of-two
input and size-derived UV scaling.

The Xbox Q3 loader also omits DarkPlaces' optional runtime portal
reconstruction and uses the map's authored PVS and node/leaf bounds with the
engine's BSP/frustum fallback. Portal-dependent SVBSP light selection is bypassed
when no graph exists. Q1 behavior is unchanged, and runtime rendering remains a
required validation gate.

The staged Xbox defaults currently select DarkPlaces' immediate mesh-submission
diagnostic and enable GL error checks. The pbGL client-array path displayed
vertical green corruption; the immediate path produced readable loading art
while keeping the same engine geometry and material inputs. Xbox adapters fill
pbGL's missing client-array and current-2D-binding queries so diagnostics and
texture restoration remain deterministic. This is a bring-up fallback, not
evidence that menu interaction or world rendering is complete.

The same generated Xbox `model_brush.c` also pre-counts Q3 patch faces before
allocating temporary tessellation records. This preserves the pinned loader's
surface and curve behavior while avoiding one scratch record for every flat BSP
face; a capacity check fails explicitly if the scan and population ever differ.

The Xbox defaults preserve:

- controller movement/look and combat bindings;
- automatic quality **OFF**;
- uncapped benchmark-friendly presentation settings;
- zero-action demo startup and controller takeover/restart behavior.

They invoke `xbox_apply_memory_profile` and then
`xbox_expect_content_profile` after normal saved configuration has loaded and
before autoplay begins. The XBE selects `retail64` below 112 MiB of detected
physical memory and `dev128` at or above 112 MiB. A mismatched disc stops with
a durable trace instead of silently testing the wrong content. The two images
are published separately under `out/<profile>/`. `dev128` is the current
playable-development milestone; it does not count as stock-memory acceptance.

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
