# Low-Memory Material Downscaling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a deterministic, bounded-source texture override during the canonical release staging path so large Nexuiz materials can load within stock 64 MiB memory.

**Architecture:** A standalone Python tool reads the effective TGA namespace from the already verified staged PK3 files, downsamples oversized images without third-party dependencies, and writes a deterministic stored override PK3. Release staging records the complete transformation identity and existing tree/XISO verification protects the resulting bytes.

**Tech Stack:** Python 3 standard library, `unittest`, ZIP/PK3, TGA.

**Spec:** `wiki/Low-Memory-Material-Downscaling.md`

## Global Constraints

- `xbox/release` remains the only end-to-end release route.
- The verified Nexuiz archive and original PK3 files remain immutable.
- Both image dimensions must be at most 512 pixels in generated overrides.
- Output ZIP entries are stored, sorted, and carry fixed metadata.
- 64 MiB is the acceptance target; 128 MiB remains diagnostic-only.
- No third-party host image library is introduced.

---

### Task 1: TGA conversion boundary

**Files:**
- Create: `tools/xbox/build_lowmem_texture_pack.py`
- Create: `tests/test_xbox_lowmem_texture_pack.py`

**Interfaces:**
- Consumes: TGA bytes from a PK3 entry.
- Produces: `decode_tga(data) -> TgaImage`, `downscale_to_limit(image, 512) -> TgaImage`, and `encode_tga(image) -> bytes`.

- [ ] Write fixtures proving 24/32-bit true-color, grayscale, RLE, orientation, alpha-aware filtering, dimension bounds, and malformed input rejection.
- [ ] Run `python3 -m unittest tests.test_xbox_lowmem_texture_pack -v` and confirm failures because the module does not exist.
- [ ] Implement strict decoding, repeated half-scale filtering, and deterministic uncompressed encoding.
- [ ] Re-run the focused tests and confirm they pass.

### Task 2: Deterministic effective-asset override pack

**Files:**
- Modify: `tools/xbox/build_lowmem_texture_pack.py`
- Modify: `tests/test_xbox_lowmem_texture_pack.py`

**Interfaces:**
- Consumes: `build_pack(pk3_paths, output_path, max_dimension=512)` with PK3 paths in engine load order.
- Produces: manifest dictionary plus `zzzz-xbox-lowmem.pk3` with original virtual paths and `xbox-lowmem-manifest.json`.

- [ ] Add failing tests for cross-pack precedence, unchanged small-image omission, stored entries, fixed metadata, sorted names, output hashes, and identical bytes across two builds.
- [ ] Run the focused test and confirm each new behavior fails for the missing pack builder.
- [ ] Implement bounded PK3 scanning and atomic deterministic output publication.
- [ ] Re-run the focused tests and confirm they pass.

### Task 3: Canonical staging and identity integration

**Files:**
- Modify: `tools/xbox/stage_classic_release.py`
- Modify: `tools/xbox/verify_release_tree.py`
- Modify: `tests/test_xbox_stage_classic_release.py`
- Modify: `tests/test_xbox_verify_release_tree.py`

**Interfaces:**
- Consumes: staged source PK3 files and `build_pack` from Task 2.
- Produces: generated pack plus schema-2 `CONTENT-IDENTITY.json` containing `derived_content` policy, count, byte size, and SHA-256.

- [ ] Add failing staging tests with a real oversized fixture and identity assertions.
- [ ] Add failing release-tree tests that reject missing, changed, or malformed derived-pack identity.
- [ ] Invoke the converter after immutable content extraction and extend identity verification.
- [ ] Run both focused suites and confirm they pass.

### Task 4: Release contract and documentation

**Files:**
- Modify: `tests/test_xbox_release_makefile.py`
- Modify: `xbox/release/README.md`
- Modify: `wiki/Memory-Budget.md`
- Modify: `wiki/Feature-Support-Matrix.md`
- Modify: `wiki/Licensing-and-Content.md`

**Interfaces:**
- Consumes: canonical `stage` target.
- Produces: documented, test-visible generated-pack gate without a second build route.

- [ ] Add a failing release-contract test that requires staging output to identify the generated low-memory pack.
- [ ] Update canonical release help/readme and memory/feature/licensing records with the exact fallback and remaining runtime gate.
- [ ] Run the release-contract suite and all host tests.

### Task 5: Full artifact verification

**Files:**
- No new production files.

**Interfaces:**
- Consumes: verified archive and pinned dependencies.
- Produces: canonical XBE/XISO and reproducible hashes.

- [ ] Run the converter against the complete staged PK3 corpus and record transformed count, pack size, and deterministic hash.
- [ ] Run `make -C xbox/release all NEXUIZ_ARCHIVE=/home/codex/src/DarkPlaces-xbox/deps/nexuiz-252.zip`.
- [ ] Run desktop `make sdl-release` and the complete host regression suite.
- [ ] Inspect `git diff --check` and ensure `xbox/xemu/` remains untracked and uncommitted.
