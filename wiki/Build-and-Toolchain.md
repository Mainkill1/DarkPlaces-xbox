# Build and Toolchain

## Toolchain

Use nxdk and every external source dependency at an exact pinned commit. The
canonical machine-readable input lock is `xbox/release/release-inputs.json`;
`xbox/classic/versions.mk` mirrors the build-facing revisions and the complete
Nexuiz archive identity.

Existing diagnostic targets remain:

```bash
make -C xbox NXDK_DIR=/path/to/nxdk
make -C xbox/inputcheck NXDK_DIR=/path/to/nxdk
```

Neither command builds the full game.

## Game target ownership

There are two engine implementation paths, but only one first-build entry:

```text
xbox/game/      modern DarkPlaces + direct RENDERPATH_XBOX development
xbox/classic/   integrated Nexuiz-era DarkPlaces + pbGL/PBKit/NV2A candidate
xbox/release/   canonical release wrapper around the integrated candidate
```

`xbox/game` remains the direct-native architecture path and must not be described
as complete while its renderer/audio source set is unfinished. `xbox/classic`
exists to get the complete Nexuiz-era engine, renderer compatibility path, audio
and network integration into one XBE early enough to expose real game/runtime
problems. Future migration from pbGL to the direct backend must preserve the same
release/content/evidence gates rather than creating another packaging system.

## Reproducible release inputs

The release wrapper locks:

```text
nxdk       29638d0b001f179b73c3513489af10ddc2986216
DarkPlaces 7349e20fba3c2b469616505907109863e8cb4a9e
pbGL       017ab17c4530bf3e2ad446a50de9b18ea6011548
libogg     e1774cd77f471443541596e09078e78fdc342e4f
libvorbis  0657aee69dec8508a0011f47f3b69d7538e9d262
```

The full Nexuiz Classic 2.5.2 archive is external content, not repository data:

```text
nexuiz-252.zip
SHA256 a5e27ebcc9775c4a490d0d3536c32e4a8f8f96b038c0b6a78d1823c37a962000
MD5    d750bc328e58df8492f8d88bdcf818cb
```

The SHA-256 is the primary content identity. The MD5 is retained to match the
historical release identity. Builds no longer depend on a fixed GitHub Actions
run or expiring `nexuiz-part00/01/02` artifacts.

## Clean-checkout build

The network phase is explicit:

```bash
make -C xbox/release bootstrap
```

That command clones/checks out only the exact locked source revisions, initializes
nxdk's recursive submodules, downloads the historical Nexuiz release to a temporary
file, verifies it, and only then installs it under ignored local `deps/`.

After bootstrap, the build is offline:

```bash
make -C xbox/release all
```

Individual gates are also available:

```bash
make -C xbox/release preflight
make -C xbox/release stage
make -C xbox/release engine
make -C xbox/release package
```

`preflight` verifies all dependency commits/submodules and the game archive before
compilation. `stage` copies the entire release `data/` tree, generates Xbox defaults
without replacing an existing game `autoexec.cfg`, and records per-file hashes.
`engine` builds only the executable. `package` produces XBE/XISO and release identity
files. `engine` and `package` do not perform network downloads.

An existing game archive may be supplied explicitly:

```bash
make -C xbox/release preflight NEXUIZ_ARCHIVE=/path/to/nexuiz-252.zip
make -C xbox/release all NEXUIZ_ARCHIVE=/path/to/nexuiz-252.zip
```

## Intended release-candidate output

```text
xbox/release/out/
  nexuiz-xbox.xbe
  nexuiz-xbox.iso
  BUILD-IDENTITY.txt
  CONTENT-IDENTITY.json
  SHA256SUMS
```

`CONTENT-IDENTITY.json` binds the ISO staging tree to the verified outer release
archive and records every staged file size/hash. `BUILD-IDENTITY.txt` records the
port, nxdk, engine, renderer-compatibility, audio-codec and content revisions.

Artifact existence proves only compile/link/package. It does not prove that the
XBE boots, presents correct NV2A frames, plays audio, completes an offline match,
hosts/joins LAN, fits stock memory or survives soak.

## Build stages

### Stage 0: toolchain smoke

Compile a tiny program from this repository, print a build identifier, present a
basic screen, and produce an XISO. This remains the independent foundation target.

### Stage 1: integrated engine compile/package

Use `xbox/release` to establish one exact executable/content identity. Build errors
are fixed against this identity rather than by adding another target or quietly
removing game services.

### Stage 2: boot and initialization

Boot the packaged game far enough to prove DarkPlaces initialization, real VFS
mounts, logging/timing/fatal paths, controller setup, renderer initialization and
audio device initialization.

### Stage 3: rendered game coverage

Prove menu/2D, BSP/lightmaps, models, effects and the zero-action demo path. Any
pbGL/NV2A incompatibility is documented and either fixed in the compatibility
boundary or replaced with a deliberate native path.

### Stage 4: playable game and LAN

Validate real offline matches under #35 and LAN hosting/joining under #36 using
the full pinned content set. A diagnostic object compile or standalone input
screen cannot close these gates.

## Build isolation

Preserve `make sdl-release` in CI. Xbox-only enum values, flags and compatibility
helpers must be guarded by `DP_PLATFORM_XBOX` or confined to Xbox sources so a
console feature cannot introduce desktop exhaustive-switch or link failures.

## Required build metadata

Every candidate should record:

- fork commit;
- nxdk revision and submodule state;
- DarkPlaces revision;
- pbGL/native-renderer revision or implementation identity;
- Ogg/Vorbis revision;
- complete content archive SHA-256;
- staged content-manifest SHA-256;
- debug/release profile;
- feature-profile identifier;
- dirty-tree marker when applicable.

## CI expectations

Desktop CI remains mandatory. The playable-Xbox workflow uses the same release
wrapper and committed lock as local builds; it must not duplicate dependency pins
inside YAML or retrieve game content from expiring build artifacts. Automated xemu
boot and workload checks are added only after the executable can emit reliable
runtime markers.
