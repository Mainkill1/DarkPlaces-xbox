# Xbox Classic Runtime Memory Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Select a safe runtime memory profile from Xbox physical memory, expose an explicit development override, and apply conservative resource ceilings without changing the classic executable's structural array limits.

**Architecture:** A platform-independent policy module owns profile parsing, threshold selection, and literal runtime ceilings. An Xbox adapter queries `MmQueryStatistics`, reads the optional writable-storage override, records telemetry, and applies retail ceilings after normal config loading through a staged console command. The canonical `xbox/release` route and one-XBE model remain unchanged.

**Tech Stack:** C99-compatible C, nxdk Xbox kernel API, Nexuiz-era DarkPlaces cvar/command APIs, Python `unittest`, canonical nxdk release Makefiles.

**Spec:** `docs/superpowers/specs/2026-09-17-retail-memory-architecture-design.md`

## Global Constraints

- Stock 64 MiB remains the release acceptance target; `dev128` is diagnostic only.
- Keep `MAX_EDICTS=8192`, `MAX_MODELS=2048`, `MAX_SOUNDS=2048`, and `SERVERLIST_TOTALSIZE=256` as compile-time structural limits for every profile.
- Automatic selection uses `dev128` only at or above 112 MiB detected physical memory; every smaller or ambiguous capacity uses `retail64`.
- An explicit `dev128` request on less than 112 MiB must fall back safely to `retail64` and report the rejection.
- `xemu64` enforces the same ceilings as `retail64` even when more physical memory is exposed.
- Retail ceilings may only reduce unsafe current values; do not raise or replace more conservative saved graphics choices.
- Automatic quality remains off, and no profile is evidence of runtime memory acceptance without measured gameplay and soak results.
- Use only the canonical `xbox/release` build route and immutable dependency inputs.

---

### Task 1: Pure profile selection and ceilings

**Files:**
- Create: `xbox/classic/include/xbox_memory_policy.h`
- Create: `xbox/classic/memory_policy_xbox.c`
- Create: `tests/test_xbox_classic_memory_profile.py`

**Interfaces:**
- Consumes: physical-memory byte count and an optional token (`auto`, `retail64`, `dev128`, or `xemu64`).
- Produces: `Xbox_MemoryPolicySelect(uint64_t total_bytes, const char *request, xbox_memory_policy_t *out)` and `Xbox_MemoryPolicyClamp(const xbox_memory_policy_t *, xbox_memory_runtime_values_t *)`.

- [ ] **Step 1: Write the failing host test**

Compile the real policy source into a harness and assert literal cases: 64/80 MiB auto select `retail64`; 111 MiB remains `retail64`; 112/128 MiB selects `dev128`; `xemu64` on 128 MiB uses retail ceilings; low-memory `dev128` is rejected to retail; invalid tokens return invalid-request status. Assert that retail clamp lowers `gl_max_size`, raises only the `gl_picmip` floor, disables bulk texture/sound precache, and enables streaming, while preserving already-more-conservative values. Assert `dev128` leaves all user values unchanged.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python3 -m unittest tests.test_xbox_classic_memory_profile -v`

Expected: FAIL because the policy header/source do not exist.

- [ ] **Step 3: Implement the minimal pure policy**

Define fixed profile names and thresholds with integer byte arithmetic. Return a status that distinguishes accepted selection, unsafe-dev128 fallback, and invalid request. Put only decisions and clamps in this module; do not include nxdk or engine headers.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `python3 -m unittest tests.test_xbox_classic_memory_profile -v`

Expected: all policy cases PASS.

### Task 2: Xbox detection, override, telemetry, and engine command

**Files:**
- Create: `xbox/classic/include/xbox_memory_profile.h`
- Create: `xbox/classic/memory_profile_xbox.c`
- Modify: `xbox/classic/sys_xbox.c`
- Modify: `xbox/classic/Makefile`
- Extend: `tests/test_xbox_classic_memory_profile.py`

**Interfaces:**
- Consumes: `MmQueryStatistics`, `E:\\UDATA\\Nexuiz\\memory-profile.txt`, the pure policy, and registered engine cvars.
- Produces: `Xbox_MemoryProfileInitialize()`, `Xbox_MemoryProfileRegisterCommands()`, and the `xbox_apply_memory_profile` console command.

- [ ] **Step 1: Write failing adapter tests**

Build the real adapter with host stubs for the kernel query, boot trace, command registration, cvar lookup/set, and override file. Assert successful 64/128 selection, query failure, missing override as `auto`, bounded valid override parsing, invalid override fallback with diagnostics, unsafe low-memory `dev128` fallback, and clamp command behavior against real mutable test cvars.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python3 -m unittest tests.test_xbox_classic_memory_profile -v`

Expected: FAIL because the adapter API is missing.

- [ ] **Step 3: Implement initialization and application**

Query total and available pages with `MM_STATISTICS.Length` initialized. Read at most 31 bytes from the override, trim ASCII whitespace, and never allocate dynamically. Record profile, total MiB, available MiB, selection reason, and diagnostic-only status in the durable boot trace. Register `xbox_apply_memory_profile`; when executed after config loading it clamps retail/xemu64 runtime values through `Cvar_FindVar`/`Cvar_SetValueQuick`, logs before/after values, and takes another available-pages snapshot. `dev128` only reports and preserves user choices.

- [ ] **Step 4: Wire startup and build ownership**

Add both profile sources to `PORT_SRCS`. In `main`, initialize the profile only after writable storage and boot trace setup but before `Host_Main`; fail early and visibly if kernel statistics cannot be queried. Call `Xbox_MemoryProfileRegisterCommands()` from `Sys_Init_Commands()`.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `python3 -m unittest tests.test_xbox_classic_memory_profile -v`

Expected: all detection, parsing, fallback, telemetry, and clamp cases PASS.

### Task 3: Apply the selected profile after saved configuration

**Files:**
- Modify: `tools/xbox/stage_classic_release.py`
- Modify: `tests/test_xbox_stage_classic_release.py`

**Interfaces:**
- Consumes: registered `xbox_apply_memory_profile` command.
- Produces: staged `xbox-defaults.cfg` that invokes the command before autoplay begins.

- [ ] **Step 1: Write the failing staging behavior test**

Stage a controlled archive and assert `xbox_apply_memory_profile` appears after the automatic-quality-off settings are established and before `xbox_demo_start`, so sound/map precache has not begun before ceilings are applied.

- [ ] **Step 2: Run the staging test and verify RED**

Run: `python3 -m unittest tests.test_xbox_stage_classic_release.ClassicReleaseStagingTests.test_memory_profile_is_applied_before_autoplay -v`

Expected: FAIL because the command is absent.

- [ ] **Step 3: Add the staged command**

Insert one `xbox_apply_memory_profile` line before the autoplay alias invocation without changing the existing config preservation order.

- [ ] **Step 4: Run staging and profile tests and verify GREEN**

Run: `python3 -m unittest tests.test_xbox_stage_classic_release tests.test_xbox_classic_memory_profile -v`

Expected: all tests PASS.

### Task 4: Document selection and exact validation boundary

**Files:**
- Modify: `wiki/Memory-Budget.md`
- Modify: `xbox/release/README.md`

**Interfaces:**
- Consumes: implemented selection thresholds, override path, and applied ceilings.
- Produces: operator instructions and accurate gate language.

- [ ] **Step 1: Document automatic and explicit selection**

Record the 112 MiB threshold, conservative gap behavior, `memory-profile.txt` tokens, unsafe override fallback, unchanged structural limits, retail runtime clamps, and the fact that `dev128` is diagnostic-only.

- [ ] **Step 2: Document the crash evidence and non-claims**

Record that the uploaded run reached first swap, audio initialization, and gamecode load before OOM in `snd_mem.c:90`. State that source/build verification does not establish boot, map load, audio completeness, gameplay, LAN, or retail64 fit.

### Task 5: Regression, canonical release, and publication

**Files:**
- Verify all changed files.

**Interfaces:**
- Consumes: completed implementation and immutable release inputs.
- Produces: verified XBE/XISO and a pushed source commit.

- [ ] **Step 1: Run all host tests**

Run: `python3 -m unittest discover -s tests -v`

Expected: zero failures.

- [ ] **Step 2: Preserve desktop build**

Run: `make sdl-release`

Expected: exit 0.

- [ ] **Step 3: Build the canonical Xbox release cleanly**

Run: `make -C xbox/release clean` then `make -C xbox/release all`

Expected: compile, link, PE-size gate, XBE creation, release-tree verification, fresh XISO creation, and XISO payload verification all pass.

- [ ] **Step 4: Perform final evidence checks**

Run `git diff --check`, confirm the release build identity matches `HEAD`, hash the XBE/XISO, and verify the worktree contains no unintended files.

- [ ] **Step 5: Commit, regenerate identity, and push master**

Commit the focused profile change, rerun `make -C xbox/release all` so `BUILD-IDENTITY.txt` names the commit, then push `master`. Report only the exact gates reached; require a new emulator/hardware run for runtime claims.
