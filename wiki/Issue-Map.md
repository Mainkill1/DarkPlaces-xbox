# Issue Map

The issue bootstrap manifest lives at `.github/port-issues.json`. Once repository Issues are enabled, run the **Bootstrap Xbox port issues** workflow. It creates labels, milestones, the detailed work issues, and a linked master tracker.

## Phase 0 — Toolchain and boot

- Pin nxdk and add the reproducible Xbox build entry point.
- Produce a bootable XBE/XISO smoke target.
- Add `DP_PLATFORM_XBOX` and the feature-pruning profile.
- Bring up DarkPlaces core initialization without the renderer.
- Add Xbox timing, logging, fatal-error, and crash diagnostics.

## Phase 1 — Platform and memory

- Implement Xbox filesystem and writable storage.
- Port threads/task queue and define the single-thread fallback.
- Establish the 64 MB budget and allocator telemetry.
- Port controller input and benchmark controls.
- Port audio with a verified no-audio mode.

## Phase 2 — NV2A renderer

- Approve the `RENDERPATH_XBOX` decision record.
- Add the backend seam and compile path.
- Device/frame lifecycle and present.
- Mesh buffers and draw submission.
- Texture formats, mipmaps, upload, and eviction.
- 2D console/menu/font.
- Quake 3 BSP visibility, world geometry, and lightmaps.
- Models and animation.
- Material translation, alpha, fog, glow, and fallbacks.
- Particles, sprites, decals, and overdraw effects.
- Dynamic lights, DOT3/normal mapping, reflections, and special-effect fallbacks.

## Phase 3 — Nexuiz stress world

- Audit Nexuiz 2.5.2 content and licenses.
- Build the Xbox asset preparation/cache pipeline.
- Add deterministic camera/demo loop.
- Build the connected mixed stress world and scaling profiles.
- Add benchmark telemetry and workload markers.

## Phase 4 — Validation and release

- Add xemu automation, CI smoke, and packaged artifacts.
- Validate/soak on standard 64 MB hardware.
- Complete licensing, release packaging, and known-limit documentation.
