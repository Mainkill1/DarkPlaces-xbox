# Nexuiz Xbox Production Engine Target Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third, production `Nexuiz Xbox` XBE/XISO target that links the real DarkPlaces client/server/menu/PRVM engine, selects `-nexuiz`, mounts packaged data, reaches normal `Host_Init`, and remains diagnosable without pretending that the native renderer/audio/LAN are complete.

**Architecture:** Keep `xbox/Makefile` and `xbox/inputcheck/Makefile` unchanged as Foundation and Controller Check diagnostics. Add `xbox/game/` as the only production application entry point, with an explicit engine source manifest and Xbox platform backend. Stage 1 uses a bootstrap video backend and null audio only to unlock the normal engine boot gate; later renderer/audio/LAN plans replace those bounded bootstrap pieces without changing the game target identity or startup contract.

**Tech Stack:** C17/C11, DarkPlaces client/server/PRVM, Nexuiz Classic game mode (`-nexuiz`), nxdk pinned by `xbox/nxdk.version`, SDL only for the already-tested controller adapter, native nxdk timing/debug/filesystem primitives, Python 3 standard-library validation, GitHub Actions.

**Spec:** `wiki/Playable-Game-and-LAN.md`

## Global Constraints

- The production title is `Nexuiz Xbox`; do not rename either existing diagnostic target.
- `xbox/game/` must link the real client, listen-server, menu, collision, filesystem and PRVM paths required by Nexuiz; a bespoke viewer or demo-only executable is not acceptable.
- Startup arguments must include `-nexuiz`; the engine's existing `GAME_NEXUIZ` entry selects `data/` as the base game directory.
- Stock 64 MiB Original Xbox remains the acceptance target; this stage records binary/static footprint but does not claim the final memory budget is solved.
- Use explicit `DP_PLATFORM_XBOX`; never pretend nxdk is an ordinary desktop Win32 platform.
- Do not link desktop OpenGL/GLES, desktop dynamic-library loading, curl/download code, Internet master-server services, or proprietary XDK components into this stage unless a later approved plan explicitly requires them.
- Preserve desktop `make sdl-release` and all existing host tests.
- The production target may use bootstrap video and null audio only until `Host_Init`; every artifact/log must state that rendering/audio are not yet production-complete.
- Compile, link, XBE package, boot, `Host_Init`, data mount, rendered frame, playable match and LAN match are separate evidence gates.
- Existing autoplay/controller/graphics-menu code remains linked where its dependencies permit, but autoplay must not be reported as working until the real engine and content execute it.

---

### Task 1: Define and test the production target boundary

**Files:**
- Create: `xbox/game/Makefile`
- Create: `xbox/game/sources.mk`
- Create: `tests/test_xbox_game_target.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `xbox/nxdk.version`, `tools/xbox/verify_nxdk.py`, DarkPlaces source files, nxdk top-level `Makefile`.
- Produces: `make -C xbox/game NXDK_DIR=<path>` -> `xbox/game/build/default.xbe` and `xbox/game/nexuiz-xbox.iso`.

- [ ] **Step 1: Write the failing production-target structure test**

Add a unittest that requires a third target and proves it is not the Foundation target:

```python
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class XboxGameTargetTests(unittest.TestCase):
    def test_game_target_is_separate_and_named_nexuiz(self):
        makefile = (ROOT / "xbox/game/Makefile").read_text(encoding="utf-8")
        self.assertIn("XBE_TITLE := Nexuiz\\ Xbox", makefile)
        self.assertIn("GEN_XISO := $(CURDIR)/nexuiz-xbox.iso", makefile)
        self.assertIn("include $(CURDIR)/sources.mk", makefile)
        self.assertNotIn("smoke/main.c", makefile)
        self.assertNotIn("inputcheck/main.c", makefile)

    def test_game_source_manifest_contains_real_engine_owners(self):
        manifest = (ROOT / "xbox/game/sources.mk").read_text(encoding="utf-8")
        for source in (
            "host.c", "cl_main.c", "sv_main.c", "fs.c", "com_game.c",
            "prvm_exec.c", "prvm_edict.c", "menu.c", "netconn.c",
            "cl_attract.c", "cl_graphics_menu.c", "xbox/controller_sdl.c",
        ):
            self.assertIn(source, manifest)
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
python3 -m unittest tests.test_xbox_game_target -v
```

Expected: FAIL because `xbox/game/Makefile` and `sources.mk` do not exist.

- [ ] **Step 3: Add the game makefile shell**

Create `xbox/game/Makefile` with these required declarations before including nxdk:

```make
.DEFAULT_GOAL := all
ROOT_DIR := $(abspath $(CURDIR)/../..)
NXDK_DIR ?= $(abspath $(ROOT_DIR)/../nxdk)
PYTHON ?= python3
export NXDK_DIR
export PATH := $(NXDK_DIR)/bin:$(PATH)

XBE_TITLE := Nexuiz\ Xbox
OUTPUT_DIR := $(CURDIR)/build
GEN_XISO := $(CURDIR)/nexuiz-xbox.iso
NXDK_SDL := y

include $(CURDIR)/sources.mk
include $(NXDK_DIR)/Makefile
```

Add the same pinned-revision preflight used by the controller diagnostic before the nxdk include; do not add an unpinned override to the production target.

- [ ] **Step 4: Create an explicit `sources.mk`**

Start with named source groups rather than importing `OBJ_SDL` wholesale:

```make
DP_XBOX_PLATFORM_SRCS := \
    $(ROOT_DIR)/sys_xbox.c \
    $(ROOT_DIR)/vid_xbox_bootstrap.c \
    $(ROOT_DIR)/thread_null.c \
    $(ROOT_DIR)/snd_null.c \
    $(ROOT_DIR)/xbox/controller_sdl.c \
    $(ROOT_DIR)/xbox/attract_policy.c

DP_XBOX_ENGINE_SRCS := \
    $(ROOT_DIR)/builddate.c \
    $(ROOT_DIR)/host.c \
    $(ROOT_DIR)/common.c \
    $(ROOT_DIR)/cmd.c \
    $(ROOT_DIR)/cvar.c \
    $(ROOT_DIR)/console.c \
    $(ROOT_DIR)/zone.c \
    $(ROOT_DIR)/fs.c \
    $(ROOT_DIR)/com_game.c \
    $(ROOT_DIR)/com_msg.c \
    $(ROOT_DIR)/com_infostring.c \
    $(ROOT_DIR)/cl_main.c \
    $(ROOT_DIR)/cl_cmd.c \
    $(ROOT_DIR)/cl_input.c \
    $(ROOT_DIR)/cl_parse.c \
    $(ROOT_DIR)/cl_demo.c \
    $(ROOT_DIR)/cl_attract.c \
    $(ROOT_DIR)/cl_graphics_menu.c \
    $(ROOT_DIR)/sv_main.c \
    $(ROOT_DIR)/sv_user.c \
    $(ROOT_DIR)/sv_phys.c \
    $(ROOT_DIR)/sv_move.c \
    $(ROOT_DIR)/sv_send.c \
    $(ROOT_DIR)/sv_ccmds.c \
    $(ROOT_DIR)/prvm_exec.c \
    $(ROOT_DIR)/prvm_edict.c \
    $(ROOT_DIR)/prvm_cmds.c \
    $(ROOT_DIR)/svvm_cmds.c \
    $(ROOT_DIR)/clvm_cmds.c \
    $(ROOT_DIR)/mvm_cmds.c \
    $(ROOT_DIR)/menu.c \
    $(ROOT_DIR)/keys.c \
    $(ROOT_DIR)/collision.c \
    $(ROOT_DIR)/world.c \
    $(ROOT_DIR)/model_shared.c \
    $(ROOT_DIR)/model_brush.c \
    $(ROOT_DIR)/model_alias.c \
    $(ROOT_DIR)/model_sprite.c \
    $(ROOT_DIR)/netconn.c \
    $(ROOT_DIR)/lhnet.c \
    $(ROOT_DIR)/mathlib.c \
    $(ROOT_DIR)/matrixlib.c

SRCS := $(DP_XBOX_PLATFORM_SRCS) $(DP_XBOX_ENGINE_SRCS)
```

This list is intentionally incomplete at first: the cross-link task below adds dependencies only when the linker proves they are required. Never solve missing symbols by importing all of desktop `OBJ_COMMON` blindly.

- [ ] **Step 5: Run the structure test and verify GREEN**

```bash
python3 -m unittest tests.test_xbox_game_target -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add xbox/game tests/test_xbox_game_target.py .gitignore
git commit -m "build: add production Nexuiz Xbox target boundary"
```

---

### Task 2: Implement the Xbox process, clock and diagnostic backend

**Files:**
- Create: `sys_xbox.c`
- Create: `tests/test_sys_xbox_contract.py`
- Modify: `sys_shared.c`
- Modify: `darkplaces.h` or the existing platform-definition header only where required to expose `DP_PLATFORM_XBOX` cleanly.

**Interfaces:**
- Produces: `int main(int argc, char **argv)`, `Sys_SDL_Init`, `Sys_SDL_Shutdown`, `Sys_SDL_GetTicks`, `Sys_SDL_Delay`, Xbox-safe fatal/log output, and the existing `Sys_Main(argc, argv)` call.
- Consumes: nxdk `GetTickCount`, `Sleep`, debug output, and the existing shared engine system API.

- [ ] **Step 1: Add a failing source-contract test**

```python
class SysXboxContractTests(unittest.TestCase):
    def test_entry_forces_nexuiz_and_calls_real_sys_main(self):
        source = (ROOT / "sys_xbox.c").read_text(encoding="utf-8")
        self.assertIn('"-nexuiz"', source)
        self.assertIn("Sys_Main", source)
        self.assertIn("DP_PLATFORM_XBOX", source)
        self.assertNotIn("LoadLibrary", source)
        self.assertNotIn("dlopen", source)
```

Also require the Xbox branch in `sys_shared.c` to disable dynamic dependency support and avoid POSIX-only headers.

- [ ] **Step 2: Run and verify RED**

```bash
python3 -m unittest tests.test_sys_xbox_contract -v
```

- [ ] **Step 3: Add `sys_xbox.c` entry behavior**

The Xbox executable has no useful desktop argv, so synthesize an engine argv containing the production identity:

```c
static char *dp_xbox_argv[] = {
    "default.xbe",
    "-nexuiz",
    "-xboxbenchmark",
    NULL
};

int main(void)
{
    Sys_SDL_Init();
    return Sys_Main(3, dp_xbox_argv);
}
```

Use `GetTickCount()` for the first monotonic millisecond implementation and `Sleep()` for bounded delays. Record the 32-bit wrap limitation in logging; later timing work under issue #25 replaces this with the final high-resolution benchmark clock.

- [ ] **Step 4: Gate desktop-only `sys_shared.c` paths**

Change the preprocessor structure so `DP_PLATFORM_XBOX` does not define `SUPPORTDLL`, does not include `dlfcn.h`, and does not select desktop dynamic-library code. The intended shape is:

```c
#if !defined(DP_PLATFORM_XBOX)
#define SUPPORTDLL
#endif
```

and platform include branches must treat Xbox separately before the desktop WIN32/POSIX split.

- [ ] **Step 5: Compile just the system backend through pinned nxdk**

```bash
export NXDK_DIR="$PWD/../nxdk"
export PATH="$NXDK_DIR/bin:$PATH"
nxdk-cc -std=c17 -DDP_PLATFORM_XBOX=1 -DDP_SMALLMEMORY=1 \
  -I. -c sys_xbox.c -o /tmp/sys_xbox.obj
```

Expected: compilation succeeds without desktop DLL/POSIX include errors.

- [ ] **Step 6: Run host tests**

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: all discovered tests pass.

- [ ] **Step 7: Commit**

```bash
git add sys_xbox.c sys_shared.c tests/test_sys_xbox_contract.py
git commit -m "feat: add Original Xbox engine system backend"
```

---

### Task 3: Add an explicit bootstrap client/video backend for the Host_Init gate

**Files:**
- Create: `vid_xbox_bootstrap.c`
- Create: `tests/test_vid_xbox_bootstrap_contract.py`
- Modify: `xbox/game/sources.mk`

**Interfaces:**
- Produces the existing VID/IN symbols required by a client engine link without claiming NV2A rendering support.
- Consumes the existing `xbox/controller_sdl.c` state adapter for input polling where available.

- [ ] **Step 1: Add a failing bootstrap-backend test**

Require explicit diagnostics and prohibit pretending to expose OpenGL:

```python
class XboxBootstrapVideoTests(unittest.TestCase):
    def test_bootstrap_backend_is_explicitly_non_renderer(self):
        source = (ROOT / "vid_xbox_bootstrap.c").read_text(encoding="utf-8")
        self.assertIn("VID_Init", source)
        self.assertIn("VID_InitMode", source)
        self.assertIn("VID_ListModes", source)
        self.assertIn("XBOX_BOOTSTRAP_VIDEO", source)
        self.assertIn("GL_GetProcAddress", source)
        self.assertIn("return NULL", source)
        self.assertNotIn("RENDERPATH_GL32", source)
        self.assertNotIn("RENDERPATH_GLES2", source)
```

- [ ] **Step 2: Run and verify RED**

```bash
python3 -m unittest tests.test_vid_xbox_bootstrap_contract -v
```

- [ ] **Step 3: Implement the minimum backend**

Implement the same public surface as `vid_null.c`, but initialize a known Xbox video mode for text diagnostics and set `cl_available = true` only if the engine can proceed through client initialization without issuing rendering commands. If that assumption is disproved by runtime or link evidence, set `cl_available = false` and make the Host_Init gate a dedicated-client boot until Task 5 introduces the real client path. Do not add fake GL function pointers.

Required behavior:

```c
void *GL_GetProcAddress(const char *name)
{
    (void)name;
    return NULL;
}

qbool GL_ExtensionSupported(const char *name)
{
    (void)name;
    return false;
}
```

Emit `XBOX_BOOTSTRAP_VIDEO` once during initialization so logs cannot be mistaken for native-renderer evidence.

- [ ] **Step 4: Compile through pinned nxdk**

```bash
nxdk-cc -std=c17 -DDP_PLATFORM_XBOX=1 -DDP_SMALLMEMORY=1 \
  -I. -c vid_xbox_bootstrap.c -o /tmp/vid_xbox_bootstrap.obj
```

- [ ] **Step 5: Run tests and commit**

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
git add vid_xbox_bootstrap.c tests/test_vid_xbox_bootstrap_contract.py xbox/game/sources.mk
git commit -m "feat: add explicit Xbox Host_Init bootstrap video backend"
```

---

### Task 4: Drive the real engine link to closure with an audited source manifest

**Files:**
- Modify: `xbox/game/sources.mk`
- Create: `tools/xbox/audit_game_link.py`
- Create: `tests/test_xbox_game_link_manifest.py`

**Interfaces:**
- Consumes: linker undefined-symbol output, `xbox/game/sources.mk`, the desktop `makefile.inc` as a reference only.
- Produces: a deterministic list of Xbox-linked engine sources and a machine-readable exclusion report.

- [ ] **Step 1: Add a test for banned desktop-only source ownership**

```python
BANNED = {
    "vid_sdl.c", "sys_sdl.c", "gl_backend.c", "gl_draw.c", "gl_rmain.c",
    "gl_rsurf.c", "gl_textures.c", "libcurl.c", "cl_video_libavw.c",
}

class XboxLinkManifestTests(unittest.TestCase):
    def test_game_manifest_excludes_desktop_renderer_and_download_stack(self):
        text = (ROOT / "xbox/game/sources.mk").read_text()
        for name in BANNED:
            self.assertNotIn(name, text)
```

- [ ] **Step 2: Run and verify current state**

The test may already pass; if it does, temporarily add one banned source to verify the test fails, then revert it before continuing.

- [ ] **Step 3: Attempt the actual production link**

```bash
make -C xbox/game NXDK_DIR="$PWD/../nxdk" V=1 2>&1 | tee /tmp/nexuiz-xbox-link.log
```

Expected on the first iteration: compile/link failures naming missing symbols or unsupported platform assumptions. Preserve the log as evidence; do not add broad source groups speculatively.

- [ ] **Step 4: Resolve undefined symbols one owner at a time**

For each undefined symbol:

1. Identify its source owner in `makefile.inc` or code search.
2. Classify it as `required-engine`, `required-platform`, `later-renderer/audio/network`, or `desktop-only`.
3. Add only `required-engine` sources to `sources.mk`.
4. For `required-platform`, implement the Xbox owner rather than importing a desktop backend.
5. For later renderer/audio/network calls reached before Host_Init, add an explicit fail-fast/bootstrap implementation with a diagnostic marker; never return silent success for a missing required service.

- [ ] **Step 5: Add `audit_game_link.py`**

Make the script parse `sources.mk` and emit JSON containing:

```json
{
  "profile": "nexuiz-xbox-production-bootstrap",
  "required_mode": "-nexuiz",
  "sources": [],
  "forbidden_sources_present": [],
  "bootstrap_backends": ["vid_xbox_bootstrap.c", "snd_null.c"],
  "production_renderer": false,
  "production_audio": false,
  "production_lan": false
}
```

Fail nonzero when a banned source appears.

- [ ] **Step 6: Require a clean link**

Repeat:

```bash
make -C xbox/game clean NXDK_DIR="$PWD/../nxdk"
make -C xbox/game NXDK_DIR="$PWD/../nxdk" V=1
```

until the target produces `default.xbe` and `nexuiz-xbox.iso` with no unresolved symbols.

- [ ] **Step 7: Run complete tests and commit**

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tools/xbox/audit_game_link.py --manifest xbox/game/sources.mk --output xbox/game/build/link-audit.json
git add xbox/game/sources.mk tools/xbox/audit_game_link.py tests/test_xbox_game_link_manifest.py
git commit -m "build: close first Nexuiz Xbox engine link set"
```

---

### Task 5: Mount real Nexuiz data roots and prove normal Host_Init

**Files:**
- Modify: `sys_xbox.c`
- Modify: filesystem platform branches in `fs.c` only where evidence requires it.
- Create: `xbox/game/README.md`
- Create: `tests/test_xbox_game_startup_contract.py`
- Modify: `xbox/port_contract.h`
- Modify: `xbox/port_contract.c`

**Interfaces:**
- Consumes: packaged directory `D:/data/` (or the exact nxdk executable-root path proven by the runtime test), engine `-nexuiz` game selection, and normal `FS_Init`/`Host_Init` flow.
- Produces: visible/logged ordered markers for `entry`, `filesystem`, `host-init`, and `stable-idle` from the actual engine executable.

- [ ] **Step 1: Add a failing startup-contract test**

Require the production target to synthesize `-nexuiz` and require the normal game directory instead of a smoke-only asset:

```python
class XboxGameStartupContractTests(unittest.TestCase):
    def test_game_entry_selects_nexuiz(self):
        text = (ROOT / "sys_xbox.c").read_text()
        self.assertIn('"-nexuiz"', text)

    def test_game_documentation_requires_data_directory(self):
        text = (ROOT / "xbox/game/README.md").read_text()
        self.assertIn("data/", text)
        self.assertIn("Host_Init", text)
```

- [ ] **Step 2: Add engine-stage logging**

Use the existing Xbox port-contract names, but emit a marker only at the actual boundary reached. `host-init` must be logged immediately after normal `Host_Init` returns successfully, not from the smoke main loop.

- [ ] **Step 3: Package a legal minimal Nexuiz bootstrap data set**

Use `tools/xbox/nexuiz_prepare.py` and a checked-in selection manifest containing only redistributable files whose hashes/license notices were verified. Do not commit the upstream bulk PK3 content itself unless issue #6/#26 explicitly approves that file for redistribution.

The game XISO staging directory must contain:

```text
default.xbe
data/
  <prepared PK3/config bootstrap files>
```

- [ ] **Step 4: Boot in xemu and capture the actual engine gate**

Launch the generated ISO and record one of these outcomes:

```text
XBOX_GAME_ENTRY
XBOX_GAME_FS_READY
XBOX_GAME_HOST_INIT
XBOX_GAME_STABLE_IDLE
```

If the run stops earlier, preserve the last marker and fatal/log text; do not move the marker forward to make the gate look successful.

- [ ] **Step 5: Add CI packaging validation**

Extend a new `.github/workflows/xbox-game-bootstrap.yml` job to build the production target and inspect the XISO contents. CI may claim only compile/link/package; xemu execution remains separate until an automated xemu runner exists.

- [ ] **Step 6: Verify and commit**

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
make -C xbox/game clean NXDK_DIR="$PWD/../nxdk"
make -C xbox/game NXDK_DIR="$PWD/../nxdk" V=1
git add sys_xbox.c fs.c xbox/game xbox/port_contract.* tests/test_xbox_game_startup_contract.py .github/workflows/xbox-game-bootstrap.yml
git commit -m "feat: boot real Nexuiz Xbox engine through Host_Init"
```

---

### Task 6: Record the production target as an intermediate gate, not a playable release

**Files:**
- Modify: `wiki/Build-and-Toolchain.md`
- Modify: `wiki/Feature-Support-Matrix.md`
- Modify: `wiki/Validation-and-Telemetry.md`
- Modify: `README.md`
- Modify: issue evidence for #7, #8, #9, #10, and #12.

**Interfaces:**
- Consumes: exact build SHA, nxdk SHA, XBE/XISO hashes, link-audit JSON, xemu marker/log.
- Produces: one unambiguous status statement: production game executable exists and reaches the measured boot gate; native rendering/audio/LAN/playability remain separate.

- [ ] **Step 1: Write the status using gate language**

The README must use wording equivalent to:

```text
`xbox/game` is the production Nexuiz Xbox executable target. It links the real
DarkPlaces/Nexuiz engine and has reached <ACTUAL VERIFIED GATE>. The current
bootstrap video/null-audio configuration is not a playable release; renderer,
audio, full content and LAN acceptance remain open.
```

Replace `<ACTUAL VERIFIED GATE>` with the evidence actually obtained before committing; never pre-write `Host_Init` if the run did not reach it.

- [ ] **Step 2: Update feature matrix truthfully**

Set the production-XBE/build rows to `implemented` only when link/package evidence exists. Keep renderer, audio, gameplay and LAN rows at their real states.

- [ ] **Step 3: Attach evidence to the existing issues**

Post exact artifact checksums and last runtime marker to the relevant issue threads; do not close #12 unless the real engine reaches its acceptance criteria.

- [ ] **Step 4: Final verification**

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
make sdl-release
make -C xbox NXDK_DIR="$PWD/../nxdk"
make -C xbox/inputcheck NXDK_DIR="$PWD/../nxdk"
make -C xbox/game NXDK_DIR="$PWD/../nxdk"
git diff --check master...HEAD
```

Required result: all commands exit 0. Separately report the latest xemu runtime marker; build success is not runtime success.

- [ ] **Step 5: Commit and open the implementation PR**

```bash
git add README.md wiki
git commit -m "docs: record Nexuiz Xbox engine boot gate"
git push -u origin port/nexuiz-game-target
```

Open a PR against the then-current `master`, with the production XBE/XISO hashes and exact boot gate in its description.

---

## Follow-on implementation plans required for a playable Option B release

This plan removes the immediate blocker—there will be a real game executable—but does **not** by itself satisfy #35 or #36. Execute these as separate plans after the engine target is stable:

1. **Native NV2A renderer:** issues #16–#22; replace `vid_xbox_bootstrap.c`, implement `RENDERPATH_XBOX`, 2D/menu/HUD, BSP/lightmaps, models, particles/effects and measured texture residency.
2. **Playable content + 64 MiB conversion pipeline:** issues #13/#14/#26/#35; pin the full Classic 2.5.2 corpus, convert/stream assets, test every map/mode, preserve gamecode and campaign/progression.
3. **Xbox audio:** issue #24; replace `snd_null.c` with bounded nxdk audio, positional SFX, music and controller-accessible volume settings.
4. **LAN networking:** issue #36; add the Xbox `lhnet` socket/lifecycle adapter, discovery/manual join/listen hosting, disconnect/rejoin and desktop-peer compatibility tests without Internet master-server behavior.
5. **Full gameplay acceptance:** #23/#25/#35; controller-only menus, bots, weapons, death/respawn, scoring, map transitions, persistence, autoplay exit/resume and fixed/adaptive graphics identity.
6. **Benchmark/soak/release:** #27–#30; continuous mixed-load demo, uncapped fixed-work mode, telemetry, xemu regressions, stock-64-MiB hardware and LAN/offline/benchmark soak.

Each follow-on plan must keep `xbox/game` as the production executable target instead of creating another standalone application.
