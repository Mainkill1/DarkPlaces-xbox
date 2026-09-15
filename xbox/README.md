# Original Xbox Foundation

This directory contains the first executable preparation slice for the Original Xbox port. It builds a repository-owned nxdk diagnostic target and defines the portable startup/capability contract that later engine backends will consume.

It does **not** link DarkPlaces yet. A successful build proves only that the pinned open-source toolchain can compile, convert, and package this repository's smoke program as an XBE/XISO.

## Pinned toolchain

The required nxdk revision is recorded in [`nxdk.version`](nxdk.version):

```text
29638d0b001f179b73c3513489af10ddc2986216
```

The build rejects a different revision by default. This avoids silently changing compiler, runtime, pbkit, or packaging behavior while the port is being established.

## Build

Clone nxdk recursively at the pinned revision, then run:

```bash
git clone --recursive https://github.com/XboxDev/nxdk.git ../nxdk
git -C ../nxdk checkout 29638d0b001f179b73c3513489af10ddc2986216
git -C ../nxdk submodule update --init --recursive

make -C xbox NXDK_DIR="$PWD/../nxdk" V=1
```

Expected outputs:

```text
xbox/build/default.xbe
xbox/darkplaces-xbox-foundation.iso
```

The makefile runs `tools/xbox/verify_nxdk.py` before accepting the artifacts. An explicitly unscored development build may use another checkout with:

```bash
make -C xbox \
  NXDK_DIR="$PWD/../nxdk" \
  ALLOW_UNPINNED_NXDK=1
```

That override is printed into the build log and must not be used as release or benchmark evidence.

## Runtime output

The smoke executable initializes a 640x480 diagnostic display and redraws:

- ordered boot markers from the portable port contract;
- source and nxdk revisions;
- the `foundation` profile name;
- the 64 MiB target profile;
- explicit unavailable capability states;
- a wrapping-safe monotonic millisecond uptime counter;
- the marker `XBOX_FOUNDATION_READY`.

The screen explicitly states that it is not the DarkPlaces engine.

## Code boundaries

- `config_xbox.h` owns the initial compile profile and capability facts.
- `port_contract.h/.c` own stable boot-stage names and capability metadata.
- `smoke/main.c` is the standalone nxdk validation program.
- `Makefile` is the only nxdk-facing build entry point in this slice.
- `tools/xbox/verify_nxdk.py` verifies the pinned checkout.

The production engine work remains in follow-on slices: Xbox platform identity in common headers, `sys_xbox.c`, filesystem roots, the diagnostic video backend, controller input, and the NV2A renderer. Those files must consume this contract rather than creating a second set of startup markers or capability flags.

## Validation

Host-side contract tests run with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The `Xbox foundation` GitHub Actions workflow additionally checks out the exact nxdk revision, builds the XBE/XISO, records SHA-256 checksums, and uploads the artifacts. The existing desktop `sdl-release` job remains a separate required regression check.
