# Direct NV2A Renderer Design

**Status:** Approved architecture for implementation on `port/nexuiz-playable-lan`.

**Scope:** Graphics only. This design replaces the non-rendering Xbox bootstrap with a real DarkPlaces client renderer targeting the Original Xbox NV2A. Audio, LAN session behavior, game-content conversion, and final performance testing remain separate tasks.

## Objective

Add a first-class `RENDERPATH_XBOX` that renders the complete pinned Nexuiz Classic gameplay workload through nxdk/pbkit without depending on desktop OpenGL, GLES, or runtime GLSL translation.

The renderer must be capable of displaying and controlling the real game: menus, console, HUD, BSP worlds, player and weapon models, projectiles, pickups, particles, sprites, beams, decals, sky, fog, alpha materials, and the selected demo route. Cosmetic effects may use explicit approximations, but gameplay-critical objects or collision cues may not disappear.

## Current Boundary

The production branch currently uses `vid_xbox_bootstrap.c`. That file intentionally keeps `cl_available = false`, returns failure from `VID_InitMode`, and provides no renderer. The engine currently defines only `RENDERPATH_GL32` and `RENDERPATH_GLES2`.

The Xbox game target already links the host/client/listen-server/VM/filesystem source set. This renderer task changes the video and rendering boundary only; it does not replace the existing engine target or create another diagnostic executable.

## Chosen Architecture

Use a direct NV2A backend behind DarkPlaces' existing engine-facing rendering interfaces.

The backend will:

1. Preserve renderer-neutral world, entity, model, visibility, batching, and UI logic where practical.
2. Replace OpenGL object/state/submission code with pbkit/NV2A implementations.
3. Add explicit Xbox branches at shader/material selection points rather than attempting to compile GLSL.
4. Select from a bounded set of prebuilt NV2A vertex-program and register-combiner recipes.
5. Use deterministic native, multipass, approximate, or disabled classifications for every requested material feature.
6. Record unsupported states and fallbacks instead of silently producing arbitrary output.

A general OpenGL shim is not part of the architecture. Small compatibility helpers may preserve existing DarkPlaces function names when they are engine interfaces, but they must issue native NV2A state and commands directly.

## Source Layout

```text
vid_xbox.c
    Video mode, framebuffer/depth setup, controller/event polling,
    renderer lifecycle, gamma metadata, begin/end frame and presentation.

r_xbox_internal.h
    Private renderer state, shared limits, handles, enums and assertions.

r_xbox_backend.c / r_xbox_backend.h
    Viewport, scissor, clear, depth, stencil, cull, blend, color mask,
    vertex/index streams, draw calls, dynamic rings and state caching.

r_xbox_texture.c / r_xbox_texture.h
    Texture allocation, conversion, swizzling, mip generation, updates,
    filtering, wrapping, default textures, residency and eviction.

r_xbox_program.c / r_xbox_program.h
    Prebuilt vertex programs and register-combiner recipes. No runtime GLSL.

r_xbox_material.c / r_xbox_material.h
    DarkPlaces material state to bounded Xbox recipe mapping, multipass
    planning, deterministic fallback selection and fallback counters.

r_xbox_draw2d.c
    Console, text, menus, HUD, loading screens and generic 2D quads.

r_xbox_world.c
    BSP batches, base textures, lightmaps, alpha surfaces, sky and fog.

r_xbox_models.c
    Alias/skeletal models, view weapons, players, projectiles, sprites,
    beams, particles and decals.

r_xbox_stats.c / r_xbox_stats.h
    Frame counters, memory counters, fallbacks and named diagnostic output.
```

`vid_xbox_bootstrap.c` remains available only to the bootstrap profile. The production game source list replaces it with `vid_xbox.c` and the renderer modules above.

## Engine Integration

### Render path identity

Add `RENDERPATH_XBOX` to `renderpath_t`. Xbox initialization sets `vid.renderpath` to this value only after native video and renderer initialization succeed.

Desktop GL32/GLES2 behavior remains unchanged. Xbox builds do not advertise fake OpenGL version or shader-language capabilities.

### Client availability

`cl_available` changes to true only after all mandatory graphics subsystems initialize:

```text
video mode
  -> color/depth targets
  -> command/push-buffer state
  -> dynamic vertex/index rings
  -> default textures
  -> fixed vertex programs/combiners
  -> 2D renderer
  -> cl_available = true
```

Any failure leaves `cl_available = false`, emits a precise stage/failure marker, releases partial resources, and causes normal engine initialization to fail honestly.

### Existing renderer files

The Xbox target will not compile `gl_backend.c` or use its OpenGL submission path. `gl_textures.c` is replaced by `r_xbox_texture.c` in the Xbox source list.

High-level renderer files may remain when they own engine traversal rather than OpenGL resources. Xbox-specific branches are permitted at the following boundaries:

- material/shader selection;
- render-target and postprocessing selection;
- texture creation/update;
- mesh state and submission;
- optional effect fallback selection.

The implementation must not scatter raw pbkit calls through world, model, client, or game code. Native commands remain inside `r_xbox_*` and `vid_xbox.c`.

## Public Renderer Interfaces

The backend exposes these native lifecycle interfaces:

```c
qbool R_Xbox_Init(const viddef_mode_t *mode);
void R_Xbox_Shutdown(void);
void R_Xbox_BeginFrame(void);
void R_Xbox_EndFrame(qbool wait_for_vblank);
void R_Xbox_InvalidateState(void);
const r_xbox_stats_t *R_Xbox_GetStats(void);
```

Engine-facing mesh and texture APIs keep the existing DarkPlaces signatures where shared code already depends on them, including:

```text
R_Mesh_CreateMeshBuffer / Update / Destroy
R_Mesh_PrepareVertices_*
R_Mesh_VertexPointer / ColorPointer / TexCoordPointer
R_Mesh_TexBind / ResetTextureState
R_Mesh_Draw
R_LoadTexture* / R_UpdateTexture / R_FreeTexture
GL_Clear / GL_BlendFunc / GL_Depth* / GL_CullFace / GL_Scissor
```

On Xbox these names are compatibility entry points into `r_xbox_*`; they do not call OpenGL.

## Frame Flow

```text
Host_Frame
  -> client simulation and visibility
  -> VID frame begin
  -> R_Mesh_Start
  -> world and entity traversal
  -> material recipe selection
  -> one or more NV2A passes
  -> 2D menu/HUD/console
  -> R_Mesh_Finish
  -> VID_Finish
  -> submit/present
```

`VID_Finish` owns presentation pacing. The renderer separately records command submission, explicit GPU waits, and intentional vblank waits so benchmark timing does not conflate them.

## Video and Render Targets

Baseline mode is 640x480, 32-bit color, fullscreen. The backend supports the video modes actually exposed by nxdk and the console configuration; it does not advertise unsupported desktop modes.

The baseline allocation is:

- two color buffers;
- one depth/stencil buffer using 24-bit depth/8-bit stencil when supported;
- a 16-bit depth fallback when 24/8 allocation is unavailable, recorded in renderer identity;
- no mandatory full-resolution postprocess target.

VSync is controlled by the existing `vid_vsync` setting. Unlimited benchmark mode may avoid intentional vblank waits while still preserving correct resource ownership and GPU completion boundaries.

## Mesh and Buffer Strategy

Static world and model data use immutable NV2A-visible buffers where lifetime and size justify allocation. Dynamic geometry uses bounded frame rings:

- 1.5 MiB dynamic vertex ring;
- 512 KiB dynamic index ring;
- 256 KiB uniform/program-constant staging;
- triple frame-fence ownership to prevent overwrite of in-flight data.

The backend supports 16-bit indices natively. Existing 32-bit element streams are split or converted into bounded 16-bit batches; conversion failure increments a counter and aborts the affected batch rather than reading invalid memory.

CPU skeletal animation remains the baseline. A GPU skinning vertex program is not required for first playable coverage.

## Texture Strategy

The texture backend accepts the image data types used by the pinned content and converts them into supported NV2A formats.

Baseline formats:

- BGRA8/RGBA8 for UI and alpha textures;
- XRGB8 for opaque high-quality textures;
- RGB565 and ARGB1555/ARGB4444 as explicit reduced-memory options;
- DXT1/DXT3/DXT5 only when the prepared content and upload path can use the supported hardware format directly;
- depth textures only for recipes that explicitly require and support them.

Textures are swizzled when required by the selected NV2A layout. Mipmaps are loaded from prepared content or generated during upload. Dynamic texture updates use bounded linear staging followed by explicit upload ownership.

Provisional renderer memory limits for the stock 64 MiB profile:

- 20 MiB resident texture hard ceiling;
- 2 MiB upload/scratch ceiling;
- 2 MiB renderer metadata and buffer-object ceiling, excluding the dynamic rings and render targets;
- one purge-and-retry attempt on allocation failure.

After purge failure, map/content loading fails with a named texture-budget error. It does not substitute an unrelated texture silently.

## Fixed Program Library

No runtime shader source is parsed or compiled. Programs are built with the pinned nxdk NV2A tooling and linked into the executable.

Mandatory vertex programs:

1. 2D passthrough.
2. Generic 3D transform with vertex color and two texture coordinates.
3. World transform with base/lightmap coordinates and fog coordinate.
4. Model transform with CPU-skinned vertices, normal and color.
5. Sprite/particle billboard transform.
6. DOT3-capable normal/tangent transform for the bounded lighting recipe.

Mandatory combiner/material recipes:

1. Solid vertex color.
2. Base texture multiplied by vertex color.
3. Base texture plus lightmap.
4. Alpha test.
5. Standard alpha blend.
6. Additive blend.
7. Modulated additive blend.
8. Fogged base/lightmap.
9. DOT3 diffuse with optional base texture.
10. Cubemap/environment approximation.
11. Deterministic fallback base-texture/fullbright recipe.

## Material Classification

Every requested material resolves to one of:

- **Native:** one supported pass.
- **Multipass:** ordered supported passes with explicit depth/blend policy.
- **Approximate:** stable reduced recipe preserving gameplay visibility.
- **Disabled:** effect omitted with a named counter and documented reason.

Initial classifications:

| Feature | Xbox treatment |
|---|---|
| Base texture, vertex color | Native |
| BSP base + lightmap | Native when texture-stage limits allow; otherwise two-pass multipass |
| Alpha test/blend/additive | Native |
| Fog | Native combiner/vertex-fog approximation |
| Sky | Native sky geometry with bounded texture recipe |
| CPU-skinned models | Native |
| Sprites, particles, beams, decals | Native generic/translucent recipes |
| Dynamic lights | Multipass bounded per-surface/per-entity recipe |
| DOT3 bump lighting | Native bounded recipe where tangent data exists |
| Water distortion/refraction | Approximate animated base texture and alpha; no screen-space refraction requirement |
| Cubemap reflections | Approximate/native cubemap recipe where format and memory permit |
| Stencil model shadows | Approximate or disabled by tier; gameplay does not depend on them |
| Shadow maps, deferred lighting | Disabled |
| Bloom, motion blur, generic postprocessing | Disabled initially |
| Arbitrary GLSL material permutations | Disabled; deterministic fallback |

Unsupported material fallback is magenta-checker only for missing/corrupt content diagnostics. Unsupported *features* fall back to base texture multiplied by vertex/entity color, or a visible fullbright color if no base texture exists.

Each unique fallback emits one warning and increments a stable counter keyed by reason. Repeated frames do not spam logs.

## 2D, Menu, HUD and Text

2D rendering is mandatory before `cl_available` becomes true. `r_xbox_draw2d.c` supports:

- textured and solid quads;
- scissor rectangles;
- color and alpha modulation;
- font atlas textures;
- console background and text;
- loading screens;
- Nexuiz menu/HUD images;
- the engine-owned controller graphics menu.

This path uses the same texture manager and command rings as 3D. It does not write directly into the framebuffer through a separate software UI path.

## World Rendering

`r_xbox_world.c` consumes existing BSP visibility and surface lists. It groups batches by recipe, texture, lightmap, blend/depth state and buffer ownership.

Required world coverage:

- Q3 BSP geometry used by Nexuiz Classic;
- PVS/visibility and frustum-culling results from existing engine code;
- base textures and lightmaps;
- vertex colors;
- alpha-tested grates/foliage;
- blended and additive surfaces;
- sky and fog;
- submodels such as doors and movers;
- deterministic fallback for unsupported shader directives.

The renderer must not draw collision-only brushes as visible world surfaces unless the existing debug setting explicitly requests them.

## Models and Effects

`r_xbox_models.c` uses existing CPU-side model loaders and animation outputs. It covers:

- player and bot models;
- first-person weapons;
- projectiles and pickups;
- brush submodels;
- sprites and billboards;
- particles;
- beams and lightning;
- decals;
- entity color, alpha, fullbright and simple lighting state.

Gameplay-critical entities always use a visible fallback if their requested cosmetic material is unsupported.

## State Cache and Safety

The backend caches all NV2A state it owns and emits commands only on changes. `R_Xbox_InvalidateState()` forces complete rebinding after target changes, external diagnostics, or recovery.

All public functions validate:

- texture unit and stream indices;
- buffer offsets and lengths;
- vertex/index counts;
- supported component formats;
- render-target ownership;
- recipe identifiers;
- dynamic-ring capacity.

Invalid state increments a named error counter, skips the unsafe draw, and reports the first occurrence. It must never submit out-of-bounds GPU addresses.

## Diagnostics and Statistics

`r_xbox_stats_t` includes at least:

```c
uint32_t frame_number;
uint32_t draw_calls;
uint32_t triangles;
uint32_t state_changes;
uint32_t texture_binds;
uint32_t texture_uploads;
uint32_t texture_upload_bytes;
uint32_t dynamic_vertex_bytes;
uint32_t dynamic_index_bytes;
uint32_t multipass_draws;
uint32_t fallback_draws;
uint32_t unsupported_materials;
uint32_t invalid_draws;
uint32_t ring_stalls;
uint32_t gpu_waits;
uint32_t vblank_waits;
size_t texture_resident_bytes;
size_t texture_peak_bytes;
```

Named initialization markers distinguish video mode, backend, textures, programs, 2D and client-ready stages.

## Source-List Changes

The production Xbox source manifest will:

- remove `vid_xbox_bootstrap.c`;
- add `vid_xbox.c` and all `r_xbox_*` modules;
- stop compiling `gl_backend.c` and `gl_textures.c` for Xbox;
- retain high-level renderer modules only where their OpenGL-specific paths are gated or replaced;
- add generated NV2A program objects;
- keep foundation and controller diagnostic targets unchanged.

The build fails if both bootstrap and production video backends are selected, or if an Xbox game profile lacks the native renderer modules.

## Failure Handling

Initialization failures are fatal to the client profile and identify the exact stage. Runtime failures use these policies:

- command-ring exhaustion: wait on the oldest owned frame fence, then continue and increment `ring_stalls`;
- texture budget pressure: LRU purge and one retry;
- unsupported material feature: deterministic fallback and counter;
- malformed/out-of-range draw: skip and counter;
- missing mandatory program/default texture/render target: stop the renderer and return to fatal engine handling;
- inability to present: report and stop rather than continuing a headless game accidentally.

## Implementation Order

The renderer is implemented in this dependency order:

1. Render-path identity and private types.
2. Video mode, color/depth targets and present.
3. State cache, command ownership and clear.
4. Dynamic/static buffers and indexed triangles.
5. Texture manager and base textured mesh.
6. Fixed program and material recipe library.
7. 2D menus/HUD/console.
8. BSP base/lightmap/alpha/sky/fog.
9. Models and gameplay effects.
10. Dynamic-light/DOT3/reflection approximations.
11. Diagnostics, feature-tier controls and source-list cutover from bootstrap.

The production client is not advertised as renderer-capable until stages 1-9 are present in the same source profile. Stages 10-11 complete the declared first playable graphics coverage and diagnostic identity.

## Verification Gates for Later Execution

No execution is part of writing this design. When testing begins, evidence must be gathered separately for:

1. Cross-compile/link of the real game target.
2. XBE/XISO packaging with the production renderer selected.
3. Video initialization and clear/present.
4. 2D menu and console visibility.
5. Real BSP world and lightmaps.
6. Player, weapon, projectile, pickup and particle visibility.
7. Complete controller-operated offline match without invisible gameplay objects.
8. Automatic demo startup and button-to-menu transition.
9. Fixed-quality benchmark and renderer counters.
10. Stock 64 MiB memory behavior and prolonged map transitions.

Passing an early gate does not imply later gates have passed.

## Explicit Non-Goals of This Task

- Audio implementation.
- LAN session completion.
- Internet services.
- Arbitrary OpenGL or GLSL compatibility.
- Deferred rendering or modern postprocessing parity.
- Final content licensing/inventory work.
- Performance claims before measured execution.
