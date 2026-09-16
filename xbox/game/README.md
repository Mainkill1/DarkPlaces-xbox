# Native Nexuiz engine target — source delivery

**Untested implementation. No compilation, unit tests, CI build/tests, emulator,
or hardware run was performed for this delivery, at the owner's request.**
Do not infer a successful link, boot or playable game from these source files.

This is the third Xbox target. Unlike `xbox/` and `xbox/inputcheck/`, its explicit
source list includes the real DarkPlaces host, client, listen-server code, PRVM,
VFS, model/collision code, menus, autoplay and controller graphics menu. It has a
native entry/system backend and calls normal `Host_Init`/`Host_Frame`.

The current `engine-bootstrap` profile intentionally keeps `cl_available=false`
and null audio. **It is not the finished playable Option B game.** The native
renderer, rendered UI, audio/codec coverage and complete gameplay/LAN sessions
remain outstanding. The title `Nexuiz Xbox` identifies the engine target, not a
claim that those remaining implementations exist. Do not hand this XBE to a
player expecting the full game or automatic rendered demo playback yet.

## Build entry for the development/test box

From the repository root, with a recursive checkout of the recorded nxdk:

```sh
make -C xbox/game \
  NXDK_DIR=/absolute/path/to/nxdk \
  CONTENT_DIR=/absolute/path/to/prepared-nexuiz
```

This command is provided for a later build, not reported as executed here. It
requires Python 3.10+, Git, the nxdk build prerequisites and real prepared content.
The existing foundation and controller diagnostics retain their own commands,
identities, source lists and outputs.

`CONTENT_DIR` must be the output of `tools/xbox/nexuiz_prepare.py stage` with
`--require-autoplay`, containing `manifest.json` and `data/xboxprep.pk3`. Include
the real `default.cfg`, `progs.dat`, `menu.dat`, generated `xbox-benchmark.cfg`,
a selected demo and its actual content dependencies. These are necessary inputs,
not proof that the selected map is complete or fits runtime memory. No dummy
QuakeC file or fabricated map is substituted when content is missing. Neither
this change nor its source artifact redistributes Nexuiz data.

Planned build outputs:

```text
xbox/game/build/disc/default.xbe
xbox/game/nexuiz-xbox.iso
xbox/game/build/nexuiz-xbox.map
xbox/game/build/generated/build-identity.json
xbox/game/build/content-identity.json
```

Only `build/disc` is packed into the XISO; metadata remains outside it. Shared
engine objects have their own `build/obj` paths, avoiding stale-object reuse with
the diagnostics. A content change forces XISO repacking. Build identity is a
content-updated generated header, so a changed Git revision rebuilds its consumers.
The new source-audit utility is an inventory, not a compiler/linker substitute:

```sh
python3 tools/xbox/audit_game_link.py --root . \
  --manifest xbox/game/sources.mk --output /work/source-audit.json
```

## Implemented source boundaries

- `sys_xbox.c`: real process entry/engine loop, high-resolution SDL counter,
  bounded sleep, native early/fatal diagnostics, optional-service failure,
  initialization/shutdown and an explicit `-nexuiz` startup.
- `xbox/platform/platform.c`: content root from the actual launched XBE's NT
  path, native directory/file attributes and removal, isolated writable UDATA
  root and write-failure detection. HDD and disc roots are not conflated.
- `fs.c`/`filematch.c`: native VFS hooks and SDL RWops, including failed handle
  duplication and zero-progress write handling. Unsupported lock requests fail
  instead of pretending an OS lock was acquired.
- `xbox/platform/zalloc.h`: allocator hooks for nxdk's static Z_SOLO zlib. JPEG
  uses its existing static-link engine path. PNG/Vorbis/other optional libraries
  still need an explicit native static binding; no DLL loader is emulated.
- `vid_xbox_bootstrap.c`: honest non-rendering frontend with the production
  controller adapter. X prints engine state; Back requests shutdown. These are
  bootstrap controls, not a substitute for the merged gameplay/menu mappings.
- `taskqueue.c`: bounded compiled worker storage and enforcement of disabled
  engine worker threads after workload sizing. SDK service threads are retained.
- `lhnet.c`/`xbox/platform/network.c`: native lwIP sockets, strict numeric IPv4/
  port parsing, real loopback, asynchronous SDK initialization and nonblocking
  interface-status sampling. Initial DHCP timeout does not spawn another stack.
  This is transport preparation, not verified LAN matchmaking or a played match.
- `netconn.c`/`no_downloads.c`: Internet master queries/advertising and external
  downloads are disabled for Option B. Existing game packet/protocol ownership
  remains in `netconn.c`; content is not silently downloaded to bypass mismatch.

The currently linked upstream `gl_*` common modules own symbols also used by its
normal dedicated-server build. They remain **dormant** during the bootstrap;
there is no selected GL32/GLES2 context and no dummy successful shader backend.
Removing them before native replacements exist would turn this into a collection
of unresolved symbols or fake stubs. This is an explicit correction to the plan's
initial blanket source exclusion, not a claim that SDL provides native NV2A GL.

## Runtime markers and limits

`XBOX_GAME_FS_READY` is printed only after real `FS_Init` returns.
`XBOX_GAME_HOST_INIT` is printed only after real `Host_Init` returns.
`XBOX_GAME_CORE_ALIVE` is printed by X during the real engine frame loop.
None is a claim that a map was rendered, a demo played or a match completed.
Automatic implicit dedicated-server map loading is suppressed in this profile so
missing rendering cannot be mistaken for a playable launch. The existing attract
hooks/configuration stay intact for the later native-client integration.

Early output uses the framebuffer plus kernel `DbgPrint`; capture of that kernel
channel in a particular xemu configuration still requires setup. There is no
claim that it automatically appears in ordinary host stdout. Video initialization
failure stops before framebuffer use. Fatal errors do not invoke an unsafe
partially initialized engine teardown.

The 1 MiB stack reservation is provisional and unmeasured. Memory-size cvars
remain unknown rather than using desktop address-space guesses or `/proc`. Total 64 MiB fit,
loading peaks, service buffers, CPU instruction coverage, port/reconnect behavior,
static codec coverage, content completeness and actual link success are unverified.
The network service initializes once per XBE lifetime because the pinned SDK's
`nxNetShutdown` does not tear down its threads. Full LAN host/join UI, reconnect
session behavior and compatible peer acceptance remain issue #36.

## Publication and next work

This source-only delivery advances the approved production engine-target plan;
no green check or binary from older diagnostics is reused as evidence. The commit
uses `[skip ci]` so the existing build/test workflows do not run on this revision.
No tests were added or executed. A source-publication job, when used to transport
these changes, only applies and commits source; it does not compile or run it.

The full release contract is still `wiki/Playable-Game-and-LAN.md`: playable
Nexuiz offline plus LAN, audio, persistent/controller UI and zero-action startup
into the demo loop. Native rendering and final game integration cannot be replaced
by this headless profile. Issues #7–#15/#18/#36 remain open until their respective
compile/link/runtime requirements have been met.
