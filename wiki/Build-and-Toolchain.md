# Build and Toolchain

## Toolchain

Use nxdk with a pinned revision. Developers may point `NXDK_DIR` at an external checkout; CI must clone the same pinned revision so a build can be reproduced later.

Existing diagnostic targets are:

```bash
make -C xbox NXDK_DIR=/path/to/nxdk
make -C xbox/inputcheck NXDK_DIR=/path/to/nxdk
```

Neither command builds the full game. The production engine needs a distinct target and output directory under issue #7, preserving the known diagnostics. Do not advertise a full-game build command before it exists.

## Build stages

### Stage 0: toolchain smoke

Compile a tiny program from this repository, print a build identifier, present a basic screen, and produce an XISO. This proves the host environment before DarkPlaces errors are mixed in.

### Stage 1: core compile

An internal core diagnostic may temporarily omit renderer/audio/network outputs. Keep its exclusions explicit and separate from the playable profile. The production [Option B](Playable-Game-and-LAN) link requires the client, local/listen server, game VMs, collision, VFS, native renderer, controller, audio, persistence and LAN transport. Omit only dependencies proved unnecessary by the actual content audit; do not blanket-remove the server or game-required codecs/VM services.

### Stage 2: boot console

Enter the DarkPlaces host loop far enough to display/log initialization and read a tiny packaged configuration file.

### Stage 3: renderer bring-up

Add only the Xbox renderer objects required for clear/present, then build capability one gate at a time.

### Stage 4: playable game and LAN

Link all required game services into the same XBE. Validate real offline matches under #35 and LAN hosting/joining under #36, then package the full audited content set. A diagnostic object compile or standalone input screen cannot close these gates.

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
