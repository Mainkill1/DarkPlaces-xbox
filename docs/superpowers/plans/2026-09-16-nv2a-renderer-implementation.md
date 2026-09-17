# Direct NV2A Renderer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the non-rendering Xbox bootstrap with a first-class `RENDERPATH_XBOX` that can render the pinned Nexuiz Classic client workload through nxdk/pbkit: video/present, meshes, textures, fixed NV2A programs, 2D UI, BSP worlds, animated models, particles, decals, fog, sky, and bounded lighting/reflection approximations.

**Architecture:** Keep DarkPlaces’ renderer-neutral traversal, batching, texture API, and draw API where practical, but replace the OpenGL backend, OpenGL texture manager, and GLSL selection on Xbox with direct NV2A modules. The production target selects prebuilt vertex programs and register-combiner recipes; unsupported features resolve to deterministic native, multipass, approximate, or disabled outcomes with counters rather than silent output changes.

**Tech Stack:** C17, nxdk commit `29638d0b001f179b73c3513489af10ddc2986216`, pbkit/NV2A, nxdk Cg shader tools, DarkPlaces renderer interfaces, Python 3 standard library for source-contract checks.

**Spec:** `docs/superpowers/specs/2026-09-16-nv2a-renderer-design.md`

## Global Constraints

- Work only on `port/nexuiz-playable-lan`; do not modify `master` directly.
- Graphics is the only subsystem in this plan. Do not add audio, change LAN session behavior, or alter content licensing/selection policy.
- Keep `xbox/Makefile` and `xbox/inputcheck/Makefile` unchanged; those diagnostics remain independently buildable.
- The production renderer uses `RENDERPATH_XBOX`; it must not claim GL32/GLES2, fake an OpenGL version, load desktop GL, or compile runtime GLSL.
- Raw pbkit/NV2A commands stay inside `vid_xbox.c` and `r_xbox_*`; world, model, client, menu, and game code must not issue native GPU commands.
- Preserve the desktop `make sdl-release` path and existing GL32/GLES2 behavior.
- Stock 64 MiB memory remains the target. Enforce the spec ceilings: 20 MiB resident textures, 2 MiB upload/scratch, 2 MiB renderer metadata/buffer objects, 1.5 MiB dynamic vertex ring, 512 KiB dynamic index ring, and 256 KiB constant staging.
- Support 16-bit native indices. Convert or split 32-bit streams; never truncate them.
- CPU skeletal animation is the initial supported path; do not make GPU skinning a dependency.
- Menus, console, HUD, loading screens, gameplay actors, projectiles, pickups, and collision cues may not disappear because a cosmetic material feature is unsupported.
- `cl_available` describes whether a client is compiled into the executable and therefore must be true before `Host_Init` selects client mode. Runtime graphics readiness is tracked separately and remains false until video, render targets, backend state, dynamic rings, default textures, mandatory programs/recipes, and 2D rendering are initialized.
- `DP_XBOX_CAP_RENDERER` remains a runtime-evidence capability bit. `DP_XBOX_NATIVE_RENDERER` is a mode-specific compiler definition emitted only when `XBOX_RENDERER=native`; do not put it unconditionally in `profile.h` or flip the capability bit merely because source was written.
- No test result, build result, xemu result, or hardware result is implied by committing source. Each verification gate is separate.

---

## File Responsibility Map

| File | Single responsibility |
|---|---|
| `vid.h` | Add the public `RENDERPATH_XBOX` identity. |
| `xbox/game/profile.h` | Keep platform/memory policy and the runtime-evidence capability bit; renderer selection stays in the Makefile. |
| `xbox/game/sources.mk` | Select exactly one Xbox video backend and the native renderer modules. |
| `xbox/game/Makefile` | Generate/link NV2A shader includes and reject conflicting renderer selections. |
| `vid_xbox.c` | Video mode, client availability, controller/events, renderer lifecycle, and presentation. |
| `r_xbox_internal.h` | Private limits, device state, buffer/texture handles, recipes, assertions, and shared helpers. |
| `r_xbox_stats.h/.c` | Renderer counters, fallback/error names, frame reset, and bounded diagnostics. |
| `r_xbox_backend.h/.c` | Viewport, state cache, clear, mesh buffers, vertex streams, draw submission, frame rings, and compatibility entry points from `gl_backend.h`. |
| `r_xbox_texture.h/.c` | Full `r_textures.h` implementation, conversion, mip layout, swizzle/upload, updates, pools, residency, and eviction. |
| `r_xbox_program.h/.c` | Upload/select precompiled NV2A vertex programs and register-combiner recipes. |
| `r_xbox_material.h/.c` | Map DarkPlaces shader modes/permutations/material flags to bounded Xbox pass plans. |
| `r_xbox_draw2d.h/.c` | Native 2D recipe readiness and quad batching used by existing `gl_draw.c` high-level UI code. |
| `r_xbox_world.h/.c` | World/lightmap batch policy and Xbox-specific world material preparation used by `gl_rsurf.c`. |
| `r_xbox_models.h/.c` | Model/effect stream preparation and visible fallback policy. |
| `gl_rmain.c` | Retain desktop GLSL path; delegate shader/material setup to Xbox planner under `RENDERPATH_XBOX`. |
| `gl_rsurf.c` | Retain renderer-neutral batch traversal; call Xbox world hooks where a native pass plan is required. |
| `r_shadow.c` | Compile out GL-only query/FBO/shadow-map paths on Xbox and route bounded dynamic lighting to Xbox recipes. |
| `r_textures.h` | Preserve public texture API; add Xbox-private fields only under `DP_PLATFORM_XBOX`. |
| `model_shared.h` | Preserve `r_meshbuffer_t`; document/use `devicebuffer` for NV2A-visible storage on Xbox. |
| `xbox/shaders/*.vs.cg`, `*.ps.cg` | Source for mandatory precompiled NV2A programs/combiner includes. |
| `tools/xbox/audit_renderer_sources.py` | Prove source ownership, exactly-one-backend selection, and absence of desktop GL objects in native mode. |
| `tests/test_xbox_renderer_contract.py` | Static public/build/source contract checks. |
| `tests/test_xbox_renderer_pure.c` | Host tests for pure ring, format, index, and material-planning helpers. |

---

### Task 1: Establish the Xbox Render-Path and Source Contract

**Status:** Source prepared on branch. Compilation and tests were not run at the owner’s request.

**Files:**
- Modify: `vid.h`
- Modify: `xbox/game/profile.h`
- Modify: `xbox/game/sources.mk`
- Modify: `xbox/game/Makefile`
- Create: `r_xbox_internal.h`
- Create: `r_xbox_stats.h`
- Create: `r_xbox_stats.c`
- Create: `tools/xbox/audit_renderer_sources.py`
- Create: `tests/test_xbox_renderer_contract.py`

**Interfaces:**
- Produces: `RENDERPATH_XBOX`, mode-specific `DP_XBOX_NATIVE_RENDERER`, `r_xbox_stats_t`, `R_Xbox_StatsBeginFrame()`, `R_Xbox_GetStats()`, and source groups `DP_XBOX_BOOTSTRAP_VIDEO_SRCS` / `DP_XBOX_NATIVE_RENDER_SRCS`.
- Consumes: existing `renderpath_t`, `xbox/game` profile, and explicit source manifest.

---

### Task 2: Implement Video Mode, Device Lifecycle, and Presentation Ownership

**Status:** Source prepared on branch. Compilation, static tests, xemu, and hardware execution were not run at the owner’s request.

**Files:**
- Create: `vid_xbox.c`
- Create: `r_xbox_backend.h`
- Create: `r_xbox_backend.c`
- Modify: `sys_xbox.c`
- Test contract: `tests/test_xbox_renderer_contract.py`

**Interfaces:**
- Consumes: `RENDERPATH_XBOX`, stats API, existing controller adapter.
- Produces: `R_Xbox_Init()`, `R_Xbox_Shutdown()`, `R_Xbox_BeginFrame()`, `R_Xbox_EndFrame()`, `R_Xbox_InvalidateState()`, and the full `VID_*` platform interface.

**Prepared behavior:**
- `vid_xbox.c` owns `XVideoSetMode`, `pb_init`, `pb_kill`, actual mode metadata, controller polling, `RENDERPATH_XBOX` selection, reverse-order cleanup, and `VID_Finish` presentation.
- `r_xbox_backend.c` owns `pb_reset`, back-buffer targeting, bounded GPU waits, `pb_finished`, optional vblank pacing, and presentation statistics.
- `sys_xbox.c` no longer initializes a diagnostic framebuffer before `Host_Init`; early failures use the kernel/debug channel.
- `cl_available` is true before `Host_Init` because it is a compile-time client capability. `xbox_video.runtime_ready` records whether native video initialization completed.
- Native video remains selectable but bootstrap remains the production default until the remaining renderer tasks are present.

---

### Task 3: Implement Native State Cache, Viewports, Clear, and Render Targets

**Files:**
- Modify: `r_xbox_internal.h`
- Modify: `r_xbox_backend.h`
- Modify: `r_xbox_backend.c`
- Create: `tests/test_xbox_renderer_pure.c`

**Interfaces:**
- Produces: DarkPlaces compatibility functions declared by `gl_backend.h`: viewport, clear, blend, depth, stencil, polygon offset, cull, color mask, scissor, framebuffer selection, and `GL_Finish()`.
- Produces pure mapping helpers: `R_Xbox_MapBlend()`, `R_Xbox_MapDepthFunc()`, `R_Xbox_MapCull()`, `R_Xbox_ValidateRect()`.

**Implementation requirements:**
- Preserve renderer-neutral viewport and scissor math currently owned by `gl_backend.c`.
- Keep public compatibility globals required by shared traversal code, but route state changes into native NV2A methods.
- Maintain a single cached state object with viewport, depth, blend, cull, scissor, color-mask, polygon-offset, active texture, bound textures, and transform matrices.
- Use pbkit back-buffer/depth ownership; do not fabricate OpenGL FBO identifiers.
- Validate rectangles, enums, offsets, and ownership before submission.
- Clear color/depth/stencil using pbkit/NV2A methods and track invalid state with named counters.

---

### Task 4: Implement Bounded Mesh Buffers and Indexed Draw Submission

**Files:**
- Modify: `r_xbox_internal.h`
- Modify: `r_xbox_backend.h`
- Modify: `r_xbox_backend.c`
- Modify: `model_shared.h`
- Extend: `tests/test_xbox_renderer_pure.c`

**Interfaces:**
- Produces the existing DarkPlaces mesh-buffer, vertex-pointer, texture-coordinate-pointer, temporary-vertex, and `R_Mesh_Draw` interfaces.
- Produces bounded ring allocation and 32-bit-to-16-bit batch conversion helpers.

**Implementation requirements:**
- Allocate the 1.5 MiB vertex ring, 512 KiB index ring, and 256 KiB constant staging under triple-frame ownership.
- Never overwrite in-flight ring regions; wait on the oldest fence and count a ring stall.
- Use native 16-bit indices. Convert or split 32-bit element arrays only when every resulting batch is representable; never truncate.
- Keep immutable buffers in contiguous NV2A-visible memory and dynamic streams in bounded rings.
- Validate counts, strides, formats, offsets, and GPU addresses before each draw.

---

### Task 5: Implement Texture Storage, Conversion, Mipmaps, and Residency

**Files:**
- Create: `r_xbox_texture.h`
- Create: `r_xbox_texture.c`
- Modify: `r_textures.h`
- Extend: `tests/test_xbox_renderer_pure.c`

**Interfaces:**
- Produces the complete public texture-pool/load/update/free/query API currently supplied by `gl_textures.c`.
- Produces Xbox-private format/layout/residency helpers.

**Implementation requirements:**
- Support BGRA8/RGBA8, XRGB8, RGB565, ARGB1555, ARGB4444, and validated DXT1/3/5 inputs.
- Compute complete mip layouts before allocation and reject integer overflow or over-budget requests.
- Swizzle only formats/layouts that require it; preserve validated compressed blocks.
- Enforce 20 MiB resident, 2 MiB upload/scratch, and 2 MiB metadata ceilings.
- Perform one LRU purge-and-retry on pressure, then fail with a named texture-budget error.
- Never silently replace valid but over-budget game content with an unrelated texture.

---

### Task 6: Add Precompiled NV2A Programs and Register-Combiner Recipes

**Files:**
- Create: `r_xbox_program.h`
- Create: `r_xbox_program.c`
- Create: `xbox/shaders/` vertex/pixel program sources required by the approved spec.
- Modify: `xbox/game/Makefile`

**Interfaces:**
- Produces program and combiner identifiers, initialization/shutdown, selection, constant upload, and build-generated include objects.

**Implementation requirements:**
- Use the pinned nxdk Cg/compiler rules; no runtime GLSL parsing or compilation.
- Include mandatory 2D, generic 3D, world/lightmap/fog, CPU-skinned model, billboard, and DOT3 transforms.
- Include solid, texture×color, base+lightmap, alpha test/blend, additive, modulated additive, fog, DOT3, cubemap, and fallback combiners.
- Fail initialization when any mandatory program or recipe is absent.

---

### Task 7: Implement Deterministic Material Planning

**Files:**
- Create: `r_xbox_material.h`
- Create: `r_xbox_material.c`
- Modify: `gl_rmain.c`
- Extend: `tests/test_xbox_renderer_pure.c`

**Interfaces:**
- Produces material pass plans classified as native, multipass, approximate, or disabled.
- Consumes DarkPlaces shader mode, permutation bits, material flags, blend/depth state, and available texture inputs.

**Implementation requirements:**
- Map all pinned-game requests to a bounded pass plan.
- Use explicit approximations for water/refraction, cubemap reflection, and shadow tiers.
- Disable deferred lighting, shadow maps, bloom, motion blur, generic postprocessing, and arbitrary GLSL permutations with named counters.
- Preserve gameplay visibility with base-texture×color or fullbright fallbacks.
- Warn once per fallback reason; do not spam per frame.

---

### Task 8: Implement Native 2D Menu, Console, HUD, and Text Coverage

**Files:**
- Create: `r_xbox_draw2d.h`
- Create: `r_xbox_draw2d.c`
- Modify: `gl_draw.c` only at the native-backend handoff points.

**Interfaces:**
- Produces native 2D readiness, quad batching, scissor, solid/textured drawing, font-atlas use, and flushing.

**Implementation requirements:**
- Use the same native texture manager, rings, program library, and frame ownership as 3D.
- Cover console, text, loading screen, game menu, HUD, Nexuiz images, and controller graphics menu.
- Do not use a separate software-framebuffer UI path.
- Keep runtime readiness false until the mandatory 2D path initializes.

---

### Task 9: Integrate BSP World, Lightmaps, Sky, Fog, and Alpha Surfaces

**Files:**
- Create: `r_xbox_world.h`
- Create: `r_xbox_world.c`
- Modify: `gl_rsurf.c`
- Modify: `r_sky.c` only at native handoff points.

**Interfaces:**
- Produces world batch classification/preparation and pass submission using existing BSP/PVS/frustum results.

**Implementation requirements:**
- Cover Q3 BSP geometry used by Nexuiz, base textures, lightmaps, vertex colors, alpha test/blend/additive, sky, fog, and brush submodels.
- Batch by recipe, texture, lightmap, blend/depth state, and buffer ownership.
- Use two-pass lightmaps only when native stage limits require it.
- Do not expose collision-only brushes outside existing debug controls.

---

### Task 10: Integrate Models and Gameplay Effects

**Files:**
- Create: `r_xbox_models.h`
- Create: `r_xbox_models.c`
- Modify the existing model/effect handoff points only as required.

**Interfaces:**
- Produces native stream preparation and visible material fallback for models, first-person weapons, players, projectiles, pickups, sprites, particles, beams, lightning, and decals.

**Implementation requirements:**
- Use existing CPU model loaders and CPU skeletal-animation output.
- Preserve entity color, alpha, fullbright, and simple lighting.
- Ensure gameplay-critical actors and effects always receive a visible fallback.

---

### Task 11: Add Bounded Dynamic Lighting, DOT3, Reflections, and Quality Tiers

**Files:**
- Modify: `r_xbox_material.c`
- Modify: `r_xbox_program.c`
- Modify: `r_shadow.c`
- Modify: controller graphics settings only to expose actually supported tiers.

**Interfaces:**
- Produces explicit quality tiers and bounded lighting/effect recipes.

**Implementation requirements:**
- Provide bounded multipass dynamic lights.
- Enable DOT3 only where tangent data and the fixed recipe exist.
- Provide cubemap/environment approximation when format and memory allow.
- Keep stencil shadows approximate/optional; disable shadow maps and deferred lighting.
- Keep auto quality OFF by default and report every adaptive/manual change.

---

### Task 12: Complete Source Cutover and Capability Diagnostics

**Files:**
- Modify: `xbox/game/Makefile`
- Modify: `xbox/game/sources.mk`
- Modify: `xbox/game/README.md`
- Modify: renderer feature documentation.

**Interfaces:**
- Produces the complete native renderer source profile as the default production selection.

**Implementation requirements:**
- Change the production default from `bootstrap` to `native` only after Tasks 1–11 exist in the same source profile.
- Retain explicit `XBOX_RENDERER=bootstrap` for diagnosis.
- Keep `DP_XBOX_CAP_RENDERER=0` until runtime evidence passes; source cutover is not runtime proof.
- Record exact native/multipass/approximate/disabled feature coverage.

---

### Task 13: Deferred Verification Gates

Testing was deliberately deferred by owner request during source preparation. When execution is authorized, collect separate evidence for:

1. Contract/audit tools.
2. Host pure-helper tests.
3. Native cross-compile/link.
4. XBE/XISO packaging.
5. Video init and clear/present.
6. Indexed textured mesh.
7. 2D console/menu/HUD.
8. BSP world/lightmaps/sky/fog/alpha.
9. Models/effects/gameplay visibility.
10. Fixed/approximate advanced material coverage.
11. Real demo loop and controller takeover.
12. Stock-64-MiB memory high-water and hardware execution.

No earlier source-preparation commit implies any one of these gates passed.
