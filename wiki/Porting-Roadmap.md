# Porting Roadmap

The phases are dependency gates. Later work may be researched in parallel, but it should not merge against an unproven earlier boundary.

## Phase 0 — Toolchain and boot

- Pin nxdk and add a reproducible build entry point.
- Produce a tiny bootable XBE/XISO from this repository.
- Add `DP_PLATFORM_XBOX` and a feature-pruned object/config profile.
- Bring up DarkPlaces core initialization without the renderer.
- Provide logging, timing, fatal-error handling, and startup diagnostics.

**Exit:** xemu and hardware show a build identifier and controlled DarkPlaces initialization path.

## Phase 1 — Platform and memory

- Implement VFS paths and writable output.
- Port threads/task queue or lock in a safe single-thread mode.
- Instrument the 64 MB memory budget.
- Add controller input.
- Add audio or a verified no-audio profile.

**Exit:** core loop reads packaged files, writes results, accepts controller commands, and holds a measured memory baseline.

## Phase 2 — NV2A renderer

- Approve the renderer decision record.
- Add `RENDERPATH_XBOX`.
- Clear/present.
- Mesh buffers and draw submission.
- Textures/mipmaps/cache.
- 2D console.
- Q3 BSP/lightmaps.
- Models/animation.
- materials/fog/alpha.
- particles/sprites/decals.
- dynamic lighting/DOT3/reflections and explicit fallbacks.

**Exit:** selected Nexuiz map subset renders with stable diagnostics.

## Phase 3 — Content and benchmark

- Audit Nexuiz 2.5.2 content/licenses.
- Build Xbox-ready asset conversion/cache.
- Add deterministic camera/demo looping.
- Build the connected mixed stress world.
- Add workload markers and scaling profiles.
- Emit detailed telemetry.

**Exit:** repeatable complete loop with all required workload zones.

## Phase 4 — Automation and release

- Automated nxdk build and XBE/XISO artifacts.
- Automated xemu startup/completion smoke.
- Retail 64 MB validation and soak.
- Performance/memory tuning.
- License-clean release packaging and known-limit documentation.

**Exit:** clean checkout to reproducible release, validated in xemu and on standard hardware.
