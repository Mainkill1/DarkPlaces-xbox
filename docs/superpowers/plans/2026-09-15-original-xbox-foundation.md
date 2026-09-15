# Original Xbox Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Establish a reproducible, reviewable Original Xbox foundation that builds a repository-owned nxdk smoke XBE/XISO and defines the platform contract later DarkPlaces engine work will consume.

**Architecture:** Keep the first slice isolated under `xbox/` and `tools/xbox/`. The nxdk target is a standalone diagnostic executable, not a fake DarkPlaces port. A small portable C contract defines boot stages and the initial capability profile so it can be host-tested before `sys_xbox.c`, `vid_xbox.c`, and the NV2A renderer are linked.

**Tech Stack:** C11, Python 3 standard library, GNU make, nxdk, GitHub Actions.

**Spec:** `wiki/Original-Xbox-Port-Design.md`, `wiki/Build-and-Toolchain.md`, issues #7, #8, and #12.

## Global Constraints

- The branch must not modify desktop renderer behavior.
- The existing `make sdl-release` workflow must remain green.
- The nxdk revision is pinned to a full 40-character commit SHA.
- The foundation target uses no SDL, OpenGL, GLES, proprietary XDK, firmware, BIOS, keys, or game content.
- The primary memory profile is 64 MiB.
- A successful smoke build proves only toolchain, XBE/XISO packaging, video/debug output, and monotonic uptime.
- Unsupported capabilities are represented explicitly; they do not return pretend success.

---

### Task 1: Add failing foundation contract tests

**Files:**
- Create: `tests/test_xbox_foundation.py`
- Modify: `.github/workflows/port-repository-checks.yml`

**Interfaces:**
- Consumes: repository paths and a host C compiler.
- Produces: static layout checks, verifier behavior tests, and an executable host test for `port_contract.c`.

- [ ] Add tests requiring `xbox/Makefile`, `xbox/nxdk.version`, `xbox/config_xbox.h`, `xbox/port_contract.h`, `xbox/port_contract.c`, `xbox/smoke/main.c`, and `tools/xbox/verify_nxdk.py`.
- [ ] Add tests requiring a full SHA pin, a non-SDL nxdk target, explicit profile/capability macros, and a diagnostic-only smoke source.
- [ ] Add a host compile-and-run test that calls `DP_XboxBootStageName()` and `DP_XboxPortCapabilities()`.
- [ ] Run the tests in pull-request CI and confirm they fail because the required foundation files are absent.

### Task 2: Implement the pinned nxdk verifier

**Files:**
- Create: `xbox/nxdk.version`
- Create: `tools/xbox/verify_nxdk.py`

**Interfaces:**
- Consumes: a pin file plus either an explicit actual SHA or an nxdk Git checkout.
- Produces: `normalize_sha(value: str) -> str`, `check_revision(expected: str, actual: str, allow_mismatch: bool = False) -> tuple[bool, str]`, and a CLI exit status.

- [ ] Normalize and validate full lowercase hexadecimal commit identifiers.
- [ ] Reject missing, malformed, mismatched, and dirty nxdk checkouts by default.
- [ ] Permit an explicit `--allow-mismatch` development override while printing the expected and actual revisions.
- [ ] Keep all behavior in Python's standard library.

### Task 3: Add the portable Xbox port contract

**Files:**
- Create: `xbox/config_xbox.h`
- Create: `xbox/port_contract.h`
- Create: `xbox/port_contract.c`

**Interfaces:**
- Produces: `dp_xbox_boot_stage_t`, `dp_xbox_port_capabilities_t`, `DP_XboxBootStageName()`, and `DP_XboxPortCapabilities()`.

- [ ] Define ordered startup markers from process entry through stable idle and fatal failure.
- [ ] Define the initial `foundation` profile, 64 MiB target, and explicit unavailable renderer/audio/network/dynamic-loading/filesystem-write capabilities.
- [ ] Return `invalid` for out-of-range stage values.
- [ ] Keep the contract compilable with an ordinary host C11 compiler and nxdk.

### Task 4: Add the repository-owned nxdk smoke target

**Files:**
- Create: `xbox/Makefile`
- Create: `xbox/smoke/main.c`
- Modify: `xbox/README.md`

**Interfaces:**
- Consumes: `NXDK_DIR` pointing to the pinned checkout.
- Produces: `xbox/build/default.xbe` and `xbox/darkplaces-xbox-foundation.iso`.

- [ ] Fail during makefile evaluation when `NXDK_DIR` is absent, invalid, or at the wrong revision unless `ALLOW_UNPINNED_NXDK=1` is explicitly supplied.
- [ ] Build only the smoke source and portable port contract.
- [ ] Initialize a 640x480 diagnostic display, print platform/profile/revision markers, and redraw a monotonic uptime counter once per second.
- [ ] State on screen and in documentation that the target is not the DarkPlaces engine.
- [ ] Keep generated objects, XBE, XISO, and build directories ignored.

### Task 5: Add cross-build CI and artifact evidence

**Files:**
- Create: `.github/workflows/xbox-foundation.yml`

**Interfaces:**
- Consumes: the pinned public nxdk revision.
- Produces: foundation test results plus uploaded XBE/XISO artifacts and checksums.

- [ ] Check out nxdk recursively at the exact pin.
- [ ] Install only documented open-source host prerequisites.
- [ ] Run the Python/host-C foundation tests.
- [ ] Verify the nxdk checkout and build the smoke target with verbose output.
- [ ] Emit SHA-256 checksums and upload the XBE/XISO.
- [ ] Keep the existing desktop CI job unchanged and require it to pass on the pull request.

### Task 6: Verify the branch and prepare review

- [ ] Run the complete foundation test suite in CI with zero failures.
- [ ] Confirm the nxdk cross-build exits successfully and uploads both artifacts.
- [ ] Confirm desktop `sdl-release` CI remains green.
- [ ] Compare the branch against `master` and verify no unrelated engine or renderer files changed.
- [ ] Open the pull request as draft and link issues #7, #8, and #12 without claiming those issues are fully complete.
