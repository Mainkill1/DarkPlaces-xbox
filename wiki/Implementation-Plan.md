# Implementation Plan

The executable work plan is stored in `.github/port-issues.json`. The **Bootstrap Xbox port issues** workflow creates the issues, milestones, labels, dependencies, acceptance criteria, and master tracker. This page defines the order in which those issues become mergeable.

## Gate 0 — Repository and toolchain

1. Record the upstream baseline and update policy.
2. Pin nxdk and create the canonical Xbox build entry point.
3. Build the repository-owned smoke XBE/XISO.
4. Add `DP_PLATFORM_XBOX` and the first-link feature profile.
5. Reach a controlled DarkPlaces core loop with diagnostic video.
6. Establish logging/fatal/timer diagnostics.
7. Add desktop-regression and Xbox-cross-compile CI.

Do not begin production renderer work against a build that cannot boot and report its identity on both xemu and hardware.

## Gate 1 — Runtime foundation

1. Establish VFS/read/write paths for HDD and XISO launches.
2. Decide and validate threading/task-queue behavior.
3. Enforce the 64 MB category budget.
4. Run QuakeC and the normal client/server update path.
5. Verify deterministic simulation and state hashes.
6. Add controller/operator controls.
7. Add audio without making it a graphics blocker.

Do not accept a content milestone that has no deterministic state sequence or measured memory envelope.

## Gate 2 — Renderer bring-up

1. Approve the `RENDERPATH_XBOX` decision record.
2. Add the backend seam and link without OpenGL.
3. Clear, submit, synchronize, and present for long loops.
4. Implement mesh/index buffers and state caching.
5. Implement textures, mipmaps, residency, and eviction.
6. Render 2D diagnostics.
7. Render Q3 BSP world/lightmaps.
8. Render required models/animation.
9. Resolve selected materials to finite NV2A recipes.
10. Batch particles/sprites/decals.
11. Add bounded lighting and special-effect workloads.

Each step must preserve previous reference cases. Unsupported features remain visible and counted until a reviewed recipe or fallback replaces them.

## Gate 3 — Benchmark product

1. Complete the content/license audit.
2. Generate deterministic Xbox-ready assets on the host.
3. Run the fixed camera path and loop controller.
4. Author the connected mixed-workload world and profiles.
5. Emit raw per-frame and per-marker telemetry.
6. Produce a desktop content/path reference.

The standard profile is frozen only after every intended zone is proven active by counters rather than screenshots alone.

## Gate 4 — Acceptance and release

1. Automate xemu execution and evidence packaging.
2. Add checkpoint visual/counter validation.
3. Pass retail 64 MB one-hour and extended soak tests.
4. Profile and remove accidental port overhead without weakening workload coverage.
5. Build a clean, manifest-approved, license-compliant release.

## Pull request slicing

A normal pull request should satisfy one child issue or one independently reviewable acceptance slice. Large issues such as BSP, textures, or materials may use multiple PRs, but each PR must leave a runnable state and update the issue checklist with evidence.

Recommended commit order inside a PR:

1. failing validation/reference case;
2. minimal implementation;
3. xemu evidence;
4. hardware evidence when required by that issue;
5. documentation and feature/memory matrix update.

## Completion source of truth

The GitHub issue tracker records execution status. Wiki pages record durable design. Result/evidence packages record proof. None substitutes for the other two.
