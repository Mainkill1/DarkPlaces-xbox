# Xbox Release Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a clean checkout unambiguous and self-contained enough that an engineer can obtain all legal external inputs, verify exact identities, stage the full Nexuiz 2.5.2 data set, and invoke one Xbox release-candidate build path without relying on expiring Actions artifacts.

**Architecture:** Keep `xbox/game` as the direct-NV2A research/backend path, but make the already-integrated `xbox/classic` target the first end-to-end release-candidate build entry because it currently owns a complete client/server/gamecode source set plus pbGL/NV2A, SDL audio and Xbox networking. Add a thin `xbox/release` wrapper and a durable dependency/content lock. No full Xbox build is run by this plan.

**Tech Stack:** GNU make, Python 3 standard library, nxdk, pbGL, Nexuiz-era DarkPlaces, libogg/libvorbis, GitHub Actions, SourceForge-hosted Nexuiz 2.5.2 archive.

**Spec:** `wiki/Playable-Game-and-LAN.md`, `wiki/Original-Xbox-Port-Design.md`, `wiki/Licensing-and-Content.md`

## Global Constraints

- Stock 64 MiB Original Xbox remains the acceptance target.
- Keep the foundation/input diagnostics separate from the game target.
- Preserve desktop `make sdl-release`.
- Do not commit retail game data, proprietary XDK material, BIOS/EEPROM/keys, or unverified assets.
- Zero-action demo startup remains a release requirement.
- LAN and stereo audio remain release requirements.
- This readiness pass performs host/static verification only; it does not claim XBE boot, rendered frames, gameplay, audio, LAN, memory fit or hardware acceptance.

---

### Task 1: Restore Desktop Build Isolation

**Files:**
- Modify: `vid.h`

**Interfaces:**
- Consumes: existing `DP_PLATFORM_XBOX` platform define.
- Produces: `RENDERPATH_XBOX` visible only to Xbox compilation units, preventing desktop exhaustive-switch warnings.

- [ ] **Step 1: Use existing failing CI as RED evidence**

Existing PR #37 CI fails with `vid_sdl.c:1913: enumeration value 'RENDERPATH_XBOX' not handled in switch [-Werror=switch]`.

- [ ] **Step 2: Guard only the Xbox enum member**

```c
typedef enum renderpath_e
{
    RENDERPATH_GL32,
    RENDERPATH_GLES2,
#ifdef DP_PLATFORM_XBOX
    RENDERPATH_XBOX
#endif
}
renderpath_t;
```

- [ ] **Step 3: Verify desktop CI later on the readiness PR**

Expected: `make sdl-release` no longer fails because a desktop-only switch sees an Xbox-only enum member.

---

### Task 2: Add a Durable Release Input Lock

**Files:**
- Modify: `xbox/classic/versions.mk`
- Create: `xbox/release/release-inputs.json`
- Create: `tests/test_xbox_release_inputs.py`
- Create: `tools/xbox/release_inputs.py`

**Interfaces:**
- Produces: `load_lock(path)`, `verify_file(path, sha256)`, `verify_checkout(path, commit)` and CLI subcommands `verify-lock`, `verify-archive`, `verify-checkouts`.

- [ ] **Step 1: Add failing host tests**

Tests require an exact schema, lowercase 40-character Git commits, lowercase 64-character SHA-256 values, archive verification, and mismatch rejection.

- [ ] **Step 2: Run repository tests and observe failure because `tools/xbox/release_inputs.py` does not exist**

- [ ] **Step 3: Add the lock and minimal verifier**

Lock exact inputs:

```text
nxdk       XboxDev/nxdk                     29638d0b001f179b73c3513489af10ddc2986216
DarkPlaces DarkPlacesEngine/DarkPlaces      7349e20fba3c2b469616505907109863e8cb4a9e
pbGL       fgsfdsfgs/pbgl                    017ab17c4530bf3e2ad446a50de9b18ea6011548
libogg     xiph/ogg                          e1774cd77f471443541596e09078e78fdc342e4f
libvorbis  xiph/vorbis                       0657aee69dec8508a0011f47f3b69d7538e9d262
Nexuiz     nexuiz-252.zip SHA-256            a5e27ebcc9775c4a490d0d3536c32e4a8f8f96b038c0b6a78d1823c37a962000
Nexuiz     nexuiz-252.zip MD5                d750bc328e58df8492f8d88bdcf818cb
```

The official archive source is the Nexuiz 2.5.2 SourceForge release page/download URL; local builds may instead supply the archive path directly.

- [ ] **Step 4: Run tests and verify pass**

---

### Task 3: Stage the Full Game Data Reproducibly

**Files:**
- Create: `tools/xbox/stage_classic_release.py`
- Create: `tests/test_xbox_stage_classic_release.py`

**Interfaces:**
- Consumes: verified `nexuiz-252.zip`.
- Produces: `xbox/classic/build/disc/data/*`, generated `autoexec.cfg`, and `CONTENT-IDENTITY.json`.

- [ ] **Step 1: Add failing archive-fixture tests**

Tests prove the stager finds the unique Nexuiz `data/` directory containing PK3s, rejects traversal/case collisions, copies all PK3s and required loose data files, and generates the zero-action demo/controller defaults.

- [ ] **Step 2: Implement bounded extraction**

The script verifies the outer archive SHA-256 before extraction, rejects symlinks/traversal/case collisions, stages only the game `data/` subtree, preserves every PK3 for full-game coverage, and records each staged file's size/SHA-256.

- [ ] **Step 3: Run tests and verify pass**

---

### Task 4: Create One Obvious Release-Candidate Entry Point

**Files:**
- Create: `xbox/release/Makefile`
- Create: `xbox/release/README.md`
- Modify: `xbox/classic/Makefile`

**Interfaces:**
- Explicit phases: `deps`, `preflight`, `stage`, `engine`, `package`, `all`.
- No hidden network download occurs as part of `engine` or `package`.

- [ ] **Step 1: Make `preflight` verify all supplied checkouts and the Nexuiz archive against `release-inputs.json`**

- [ ] **Step 2: Make `stage` invoke the audited content stager**

- [ ] **Step 3: Make `engine` invoke `xbox/classic` with explicit paths**

- [ ] **Step 4: Make `package` produce the XBE/XISO plus build/content identity files**

- [ ] **Step 5: Document exact clean-checkout commands and current validation boundary**

`xbox/game` remains documented as the direct-native renderer development path; `xbox/release` is the single first-build entry point so an engineer does not have to guess between targets.

---

### Task 5: Remove Expiring Artifact Dependency from CI

**Files:**
- Modify: `.github/workflows/xbox-playable.yml`

**Interfaces:**
- Workflow uses the same committed lock as local builds.
- It downloads the official Nexuiz 2.5.2 archive, verifies SHA-256 and MD5, then invokes `xbox/release`.

- [ ] **Step 1: Remove hard-coded Actions run/artifact IDs**

- [ ] **Step 2: Checkout external source repositories using values from the committed lock/versions file**

- [ ] **Step 3: Download the archive from the committed official URL and verify it before staging**

- [ ] **Step 4: Delegate staging/build/package to `xbox/release/Makefile` instead of duplicating release logic in YAML**

- [ ] **Step 5: Do not manually dispatch the full Xbox build during this readiness pass**

---

### Task 6: Final Static Readiness Audit

**Files:**
- Modify: `README.md`
- Modify: `wiki/Build-and-Toolchain.md`
- Modify: `wiki/Licensing-and-Content.md`

**Interfaces:**
- Produces one documented answer to: what is built, where dependencies come from, how identities are verified, and which runtime gates remain unproven.

- [ ] **Step 1: Run host/unit repository checks through PR CI**

- [ ] **Step 2: Confirm no workflow references run `35155351439` or `nexuiz-part00/01/02`**

- [ ] **Step 3: Confirm the release lock and `versions.mk` agree**

- [ ] **Step 4: Confirm desktop `sdl-release` CI returns green**

- [ ] **Step 5: Stop before manually invoking the full Xbox build**
