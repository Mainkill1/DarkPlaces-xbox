# Build and Toolchain

## Toolchain

Use nxdk with a pinned revision. Developers may point `NXDK_DIR` at an external checkout; CI must clone the same pinned revision so a build can be reproduced later.

The first Xbox build should live behind a clear entry point such as:

```bash
make xbox-smoke NXDK_DIR=/path/to/nxdk
make xbox-debug NXDK_DIR=/path/to/nxdk
make xbox-release NXDK_DIR=/path/to/nxdk
```

The final names are decided in the build issue, but all targets must emit an XBE and optionally an XISO into a dedicated ignored output directory.

## Build stages

### Stage 0: toolchain smoke

Compile a tiny program from this repository, print a build identifier, present a basic screen, and produce an XISO. This proves the host environment before DarkPlaces errors are mixed in.

### Stage 1: core compile

Compile a curated DarkPlaces object set with renderer, audio, networking, DLL loading, video capture, ODE, XMP, and other optional dependencies disabled. Record every exclusion in the feature matrix.

### Stage 2: boot console

Enter the DarkPlaces host loop far enough to display/log initialization and read a tiny packaged configuration file.

### Stage 3: renderer bring-up

Add only the Xbox renderer objects required for clear/present, then build capability one gate at a time.

## Build isolation

Do not overload the existing desktop target with Xbox assumptions. Preserve `make sdl-release` in CI. The Xbox target may reuse shared object lists, but it should own its compiler flags, static dependency policy, output names, and packaging.

## Required build metadata

Every XBE should expose:

- fork commit;
- nxdk revision;
- debug/release profile;
- feature-profile identifier;
- content-pack identifier;
- build date;
- optional dirty-tree marker for local builds.

## CI expectations

Desktop CI remains mandatory. Xbox CI should initially prove compilation/linking/XBE packaging. Automated xemu boot and workload checks are added only after the executable can emit a reliable completion marker.
