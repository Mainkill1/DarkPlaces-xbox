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
- `cl_available` remains false until video, render targets, backend state, dynamic rings, default textures, mandatory programs/recipes, and 2D rendering are all initialized.
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
| `r_xbox_backend.h/.c` | Viewport/state cache, clear, mesh buffers, vertex streams, draw submission, frame rings, and compatibility entry points from `gl_backend.h`. |
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

- [ ] **Step 1: Write the failing source-contract test**

```python
# tests/test_xbox_renderer_contract.py
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

class XboxRendererContractTests(unittest.TestCase):
    def test_renderpath_and_native_profile_exist(self):
        vid = (ROOT / "vid.h").read_text(encoding="utf-8")
        profile = (ROOT / "xbox/game/profile.h").read_text(encoding="utf-8")
        makefile = (ROOT / "xbox/game/Makefile").read_text(encoding="utf-8")
        self.assertIn("RENDERPATH_XBOX", vid)
        self.assertIn("-DDP_XBOX_NATIVE_RENDERER=1", makefile)
        self.assertIn("#define DP_XBOX_CAP_RENDERER 0", profile)

    def test_native_and_bootstrap_backends_are_mutually_exclusive(self):
        makefile = (ROOT / "xbox/game/Makefile").read_text(encoding="utf-8")
        sources = (ROOT / "xbox/game/sources.mk").read_text(encoding="utf-8")
        self.assertIn("XBOX_RENDERER ?= bootstrap", makefile)
        self.assertIn("DP_XBOX_BOOTSTRAP_VIDEO_SRCS", sources)
        self.assertIn("DP_XBOX_NATIVE_RENDER_SRCS", sources)
        self.assertRegex(makefile, re.compile(r"XBOX_RENDERER.*bootstrap.*native", re.S))

    def test_native_manifest_has_no_desktop_backend_or_texture_implementation(self):
        audit = ROOT / "tools/xbox/audit_renderer_sources.py"
        self.assertTrue(audit.is_file())
        text = (ROOT / "xbox/game/sources.mk").read_text(encoding="utf-8")
        native = text.split("DP_XBOX_NATIVE_RENDER_SRCS :=", 1)[1].split("\n\n", 1)[0]
        self.assertNotIn("gl_backend.c", native)
        self.assertNotIn("gl_textures.c", native)
        self.assertNotIn("vid_xbox_bootstrap.c", native)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the contract test and confirm the missing identifiers fail**

Run:

```bash
python3 -m unittest tests.test_xbox_renderer_contract -v
```

Expected: failures for missing `RENDERPATH_XBOX`, the mode-specific native compiler definition, and native source groups.

- [ ] **Step 3: Add public identity and private stats types**

Add to `renderpath_t` in `vid.h`:

```c
typedef enum renderpath_e
{
    RENDERPATH_GL32,
    RENDERPATH_GLES2,
    RENDERPATH_XBOX
}
renderpath_t;
```

Keep this existing runtime-evidence line in `xbox/game/profile.h` unchanged:

```c
#define DP_XBOX_CAP_RENDERER 0
```

Do not define `DP_XBOX_NATIVE_RENDERER` unconditionally in the profile. Task 1 adds it to `GAME_FLAGS` only for native-mode objects.

Create `r_xbox_stats.h` with exactly the counters from the approved spec and these APIs:

```c
typedef struct r_xbox_stats_s
{
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
} r_xbox_stats_t;

void R_Xbox_StatsBeginFrame(void);
void R_Xbox_StatsResetAll(void);
r_xbox_stats_t *R_Xbox_StatsMutable(void);
const r_xbox_stats_t *R_Xbox_GetStats(void);
void R_Xbox_StatsWarnOnce(uint32_t reason_bit, const char *message);
```

- [ ] **Step 4: Split source ownership without cutting over prematurely**

In `xbox/game/sources.mk`, define:

```make
DP_XBOX_BOOTSTRAP_VIDEO_SRCS := vid_xbox_bootstrap.c

DP_XBOX_NATIVE_RENDER_SRCS := \
    vid_xbox.c r_xbox_stats.c r_xbox_backend.c r_xbox_texture.c \
    r_xbox_program.c r_xbox_material.c r_xbox_draw2d.c \
    r_xbox_world.c r_xbox_models.c
```

Retain high-level `gl_draw.c`, `gl_rmain.c`, and `gl_rsurf.c` in a renamed `DP_XBOX_HIGHLEVEL_RENDER_SRCS`; remove `gl_backend.c` and `gl_textures.c` from native ownership. Keep bootstrap as the default selection until Task 12.

In `xbox/game/Makefile` accept exactly:

```make
XBOX_RENDERER ?= bootstrap
ifeq ($(XBOX_RENDERER),native)
GAME_RENDER_SOURCES := $(DP_XBOX_NATIVE_RENDER_SRCS) $(DP_XBOX_HIGHLEVEL_RENDER_SRCS)
GAME_FLAGS += -DDP_XBOX_NATIVE_RENDERER=1
else ifeq ($(XBOX_RENDERER),bootstrap)
GAME_RENDER_SOURCES := $(DP_XBOX_BOOTSTRAP_VIDEO_SRCS) $(DP_XBOX_DORMANT_RENDER_SRCS)
GAME_FLAGS += -DDP_XBOX_RENDERER_BOOTSTRAP=1
else
$(error XBOX_RENDERER must be native or bootstrap)
endif
```

- [ ] **Step 5: Implement source audit**

`tools/xbox/audit_renderer_sources.py` must parse `sources.mk` and fail when:

- native mode contains `vid_xbox_bootstrap.c`, `gl_backend.c`, or `gl_textures.c`;
- native mode omits any module named in `DP_XBOX_NATIVE_RENDER_SRCS`;
- bootstrap and native video backends appear in the same resolved list;
- `RENDERPATH_XBOX` is absent or native mode does not emit `-DDP_XBOX_NATIVE_RENDERER=1`;
- foundation/inputcheck makefiles reference production renderer sources.

- [ ] **Step 6: Run contract and audit**

```bash
python3 -m unittest tests.test_xbox_renderer_contract -v
python3 tools/xbox/audit_renderer_sources.py \
  --root . \
  --manifest xbox/game/sources.mk \
  --mode native
```

Expected: PASS; audit prints the resolved native renderer module list.

- [ ] **Step 7: Commit**

```bash
git add vid.h xbox/game/profile.h xbox/game/sources.mk xbox/game/Makefile \
  r_xbox_internal.h r_xbox_stats.h r_xbox_stats.c \
  tools/xbox/audit_renderer_sources.py tests/test_xbox_renderer_contract.py
git commit -m "render: define native Xbox renderer boundary"
```

---

### Task 2: Implement Video Mode, Device Lifecycle, and Presentation Ownership

**Files:**
- Create: `vid_xbox.c`
- Create: `r_xbox_backend.h`
- Create: `r_xbox_backend.c`
- Modify: `xbox/game/sources.mk`
- Test: `tests/test_xbox_renderer_contract.py`

**Interfaces:**
- Consumes: `RENDERPATH_XBOX`, stats API, existing controller adapter.
- Produces: `R_Xbox_Init()`, `R_Xbox_Shutdown()`, `R_Xbox_BeginFrame()`, `R_Xbox_EndFrame()`, `R_Xbox_InvalidateState()`, and the full `VID_*` platform interface.

- [ ] **Step 1: Extend the failing contract test for mandatory lifecycle calls**

Require `vid_xbox.c` to contain these exact calls and state transitions:

```python
def test_native_video_owns_pbkit_lifecycle(self):
    source = (ROOT / "vid_xbox.c").read_text(encoding="utf-8")
    for token in (
        "XVideoSetMode",
        "pb_init",
        "pb_kill",
        "pb_reset",
        "pb_target_back_buffer",
        "pb_finished",
        "R_Xbox_Init",
        "R_Xbox_Shutdown",
        "RENDERPATH_XBOX",
    ):
        self.assertIn(token, source)
    self.assertIn("cl_available = false", source)
    self.assertIn("cl_available = true", source)
```

- [ ] **Step 2: Implement video-mode enumeration and selection**

`VID_ListModes()` advertises only modes the backend is prepared to initialize. Start with:

```c
static const vid_mode_t xbox_modes[] =
{
    {640, 480, 32, 60, 1, 1},
};
```

`VID_InitMode()` must:

1. reject windowed, stereo, MSAA, non-32-bit, or unsupported dimensions;
2. call `XVideoSetMode(640, 480, 32, REFRESH_DEFAULT)` and check its return;
3. call `pb_init()` and record the exact failure code;
4. populate `vid.mode`, texture-size limits, draw-buffer count, and support flags without fake GL versions;
5. call `R_Xbox_Init(mode)`;
6. set `vid.renderpath = RENDERPATH_XBOX`;
7. set `cl_available = true` only if `R_Xbox_Init()` reports every mandatory subsystem ready.

- [ ] **Step 3: Move production controller/event handling into `vid_xbox.c`**

Reuse the merged `DP_ControllerSDL_*`, `DP_ButtonGate_*`, `VID_ApplyJoyState()`, and attract-mode policy. Do not keep bootstrap-only X/Back behavior. `VID_BuildJoyState()` must expose normal gameplay/menu state.

- [ ] **Step 4: Implement frame ownership**

Use this order:

```c
void R_Xbox_BeginFrame(void)
{
    R_Xbox_StatsBeginFrame();
    pb_reset();
    pb_target_back_buffer();
    R_Xbox_InvalidateState();
}

void R_Xbox_EndFrame(qbool wait_for_vblank)
{
    if (wait_for_vblank)
    {
        pb_wait_for_vbl();
        R_Xbox_StatsMutable()->vblank_waits++;
    }
    while (pb_busy())
        R_Xbox_StatsMutable()->gpu_waits++;
    while (pb_finished())
        ;
}
```

`VID_Finish()` calls `R_Xbox_EndFrame(vid_vsync.integer != 0)`. It must report present failure and stop the client rather than silently continuing headless.

- [ ] **Step 5: Implement partial-init cleanup**

Track flags for video-mode set, pbkit initialized, backend initialized, and controller initialized. `VID_Shutdown()` tears down in reverse order and is idempotent.

- [ ] **Step 6: Run static lifecycle checks**

```bash
python3 -m unittest tests.test_xbox_renderer_contract -v
```

Expected: PASS. This task does not claim a successful Xbox build or presented frame.

- [ ] **Step 7: Commit**

```bash
git add vid_xbox.c r_xbox_backend.h r_xbox_backend.c \
  xbox/game/sources.mk tests/test_xbox_renderer_contract.py
git commit -m "render: add Xbox video and presentation lifecycle"
```

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

- [ ] **Step 1: Write host tests for pure mappings**

```c
/* tests/test_xbox_renderer_pure.c */
#include <assert.h>
#include "r_xbox_backend.h"

int main(void)
{
    r_xbox_blend_state_t blend;
    assert(R_Xbox_MapBlend(GL_ONE, GL_ZERO, &blend));
    assert(!blend.enabled);
    assert(R_Xbox_MapBlend(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, &blend));
    assert(blend.enabled);
    assert(!R_Xbox_MapBlend(0x7fffffff, GL_ONE, &blend));

    assert(R_Xbox_ValidateRect(0, 0, 640, 480, 640, 480));
    assert(!R_Xbox_ValidateRect(-1, 0, 1, 1, 640, 480));
    assert(!R_Xbox_ValidateRect(639, 479, 2, 2, 640, 480));
    return 0;
}
```

- [ ] **Step 2: Extract renderer-neutral viewport math from `gl_backend.c`**

Move/copy these implementations into `r_xbox_backend.c` without qgl calls:

- `R_Viewport_TransformToScreen`
- `R_ScissorForBBox`
- `R_Viewport_InitOrtho`
- `R_Viewport_InitOrtho3D`
- `R_Viewport_InitPerspective`
- `R_Viewport_InitPerspectiveInfinite`
- `R_Viewport_InitCubeSideView`
- `R_Viewport_InitRectSideView`
- `R_SetViewport`
- `R_GetViewport`
- `R_EntityMatrix`

Keep the existing public globals (`gl_viewport`, matrices, and polygon/quad element arrays) because high-level code consumes them; document that the names are ABI compatibility, not OpenGL ownership.

- [ ] **Step 3: Define one cached native state object**

`r_xbox_state_t` must include:

```c
qbool initialized;
qbool frame_active;
int width, height;
int blend_src, blend_dst;
int depth_func;
qbool depth_test, depth_write;
int cull_face;
qbool scissor_test;
int scissor[4];
int color_mask;
float depth_range[2];
float polygon_offset[2];
float color[4];
unsigned int active_texture;
rtexture_t *bound_textures[4];
matrix4x4_t model, view, projection, modelview, modelviewprojection;
```

Initialize every field to an impossible/sentinel value so the first draw emits complete state.

- [ ] **Step 4: Implement compatibility state entry points**

Implement the `GL_*` names as native state translation. Each setter validates arguments, emits NV097 state only when changed, and increments `state_changes`. Unsupported subtractive blend requests return a deterministic additive/alpha fallback through the material planner and increment a fallback reason.

- [ ] **Step 5: Implement clear and render-target policy**

`GL_Clear()` supports the default back-buffer color plus depth/stencil target. `R_Mesh_CreateFramebufferObject()` returns `0` for the default target and rejects offscreen requests until a later recipe explicitly owns one. `R_Mesh_SetRenderTargets(0)` is valid; nonzero targets increment `invalid_draws` and emit one warning.

- [ ] **Step 6: Compile and run the pure helper test**

```bash
cc -std=c17 -Wall -Wextra -Werror \
  -DDP_XBOX_RENDERER_TEST=1 -I. \
  r_xbox_stats.c r_xbox_backend.c tests/test_xbox_renderer_pure.c \
  -o /tmp/test_xbox_renderer_pure
/tmp/test_xbox_renderer_pure
```

Expected: exit 0. The `DP_XBOX_RENDERER_TEST` path excludes pbkit emission but executes the same validation/mapping logic.

- [ ] **Step 7: Commit**

```bash
git add r_xbox_internal.h r_xbox_backend.h r_xbox_backend.c \
  tests/test_xbox_renderer_pure.c
git commit -m "render: add native Xbox state and clear backend"
```

---

### Task 4: Implement Contiguous Buffers, Dynamic Rings, and Indexed Draw Submission

**Files:**
- Modify: `model_shared.h`
- Modify: `r_xbox_internal.h`
- Modify: `r_xbox_backend.h`
- Modify: `r_xbox_backend.c`
- Modify: `tests/test_xbox_renderer_pure.c`

**Interfaces:**
- Produces: existing `R_Mesh_CreateMeshBuffer`, `R_Mesh_UpdateMeshBuffer`, `R_Mesh_DestroyMeshBuffer`, pointer/preparation APIs, `R_Mesh_Draw`, and pure helpers `R_Xbox_RingReserve()` / `R_Xbox_ConvertIndices16()`.

- [ ] **Step 1: Add failing ring and index tests**

Test:

- aligned allocations;
- exact-end allocation;
- wrap only after the owning fence is retired;
- rejection when size exceeds ring capacity;
- conversion of valid 32-bit indices;
- rejection/splitting request when an index exceeds `65535`;
- rejection when `firstvertex + index` exceeds supplied vertex count.

Use signatures:

```c
qbool R_Xbox_RingReserve(
    r_xbox_ring_t *ring,
    size_t bytes,
    size_t alignment,
    uint32_t frame_id,
    r_xbox_ring_slice_t *out);

qbool R_Xbox_ConvertIndices16(
    const int *source,
    size_t count,
    int firstvertex,
    int numvertices,
    uint16_t *destination,
    size_t destination_count);
```

- [ ] **Step 2: Use `r_meshbuffer_t.devicebuffer` as Xbox ownership**

Do not change desktop fields. Under Xbox:

- `devicebuffer` is an `MmAllocateContiguousMemoryEx` allocation;
- `bufferobject` remains zero;
- `size`, index/uniform/dynamic flags retain their current meaning;
- static updates copy into owned write-combined memory;
- dynamic updates use the appropriate frame ring;
- destroy releases only owned static allocations and removes the record.

- [ ] **Step 3: Allocate bounded rings**

During backend init allocate:

```c
R_XBOX_DYNAMIC_VERTEX_BYTES = 1536 * 1024;
R_XBOX_DYNAMIC_INDEX_BYTES = 512 * 1024;
R_XBOX_CONSTANT_BYTES = 256 * 1024;
R_XBOX_FRAMES_IN_FLIGHT = 3;
```

Each frame slot stores begin/end offsets and a fence sequence. Ring exhaustion waits only for the oldest owning frame and increments `ring_stalls`.

- [ ] **Step 4: Implement vertex stream state**

Support the formats actually used by DarkPlaces:

- float position 2/3/4;
- float color4;
- unsigned-byte color4 normalized;
- float texture coordinates 2/3/4;
- unsigned-byte skeletal indices/weights only for CPU-side preparation, not GPU skinning.

Reject unsupported component/type combinations before GPU submission.

- [ ] **Step 5: Implement indexed and non-indexed draws**

`R_Mesh_Draw()`:

1. validates all ranges and bound streams;
2. prefers existing 16-bit index buffers;
3. converts 32-bit client indices into the dynamic index ring when possible;
4. splits a batch on a vertex-window boundary when conversion requires more than 16-bit indices;
5. submits packed index batches through pbkit;
6. updates draw/triangle/dynamic byte counters.

Never cast an `int *` element array to `uint16_t *`.

- [ ] **Step 6: Run pure tests**

Use the Task 3 host command. Expected: all ring/index/state tests exit 0.

- [ ] **Step 7: Commit**

```bash
git add model_shared.h r_xbox_internal.h r_xbox_backend.h \
  r_xbox_backend.c tests/test_xbox_renderer_pure.c
git commit -m "render: add Xbox buffers and indexed submission"
```

---

### Task 5: Replace OpenGL Texture Ownership with an NV2A Texture Manager

**Files:**
- Modify: `r_textures.h`
- Create: `r_xbox_texture.h`
- Create: `r_xbox_texture.c`
- Modify: `r_xbox_internal.h`
- Modify: `r_xbox_backend.c`
- Modify: `tests/test_xbox_renderer_pure.c`

**Interfaces:**
- Implements the complete public API in `r_textures.h`.
- Produces pure helpers `R_Xbox_TextureLayout()`, `R_Xbox_ChooseTextureFormat()`, and `R_Xbox_SwizzleOffset2D()`.

- [ ] **Step 1: Add texture-layout tests**

Cover:

- BGRA/RGBA/XRGB 32-bit pitch and byte totals;
- RGB565/ARGB1555/ARGB4444 pitch;
- DXT1 versus DXT3/5 block sizes;
- full mip-chain byte count;
- NPOT dimensions;
- overflow rejection;
- swizzle offsets for known 2x2, 4x4, and 8x8 coordinates;
- format choice for alpha, low-precision, and opaque inputs.

- [ ] **Step 2: Extend `rtexture_t` only under Xbox**

Keep current public fields. Add guarded private ownership:

```c
#ifdef DP_PLATFORM_XBOX
void *xbox_pixels;
size_t xbox_bytes;
uint32_t xbox_gpu_offset;
uint32_t xbox_format;
uint32_t xbox_pitch;
uint16_t xbox_width, xbox_height, xbox_depth, xbox_miplevels;
uint32_t xbox_flags;
uint32_t xbox_last_used_frame;
char xbox_identifier[MAX_QPATH];
struct rtexture_s *xbox_pool_next;
#endif
```

Define a real Xbox `rtexturepool_t` list under the same guard.

- [ ] **Step 3: Implement all `r_textures.h` entry points**

Implement 2D, cube, update, purge, pool, width/height/flags, dirty, clear, stats, dynamic callback, and `R_RealGetTexture`. Explicitly reject unsupported 3D/depth/render-buffer requests unless a material recipe owns them.

- [ ] **Step 4: Enforce residency and scratch limits**

Before allocation:

1. compute all mip bytes with checked arithmetic;
2. purge least-recently-used nonpersistent textures until under 20 MiB;
3. make one allocation retry;
4. report `XBOX_TEXTURE_BUDGET_EXCEEDED` and fail if still over budget.

The upload/scratch allocator cannot exceed 2 MiB.

- [ ] **Step 5: Convert and upload**

Implement palette expansion, RGBA/BGRA conversion, optional alpha multiplication, 16-bit conversion, mip generation, swizzle, and direct DXT upload when input is already a supported DXT type. Record upload count/bytes.

- [ ] **Step 6: Bind through native backend**

`R_Mesh_TexBind()` resolves dirty textures, validates unit 0–3, writes NV2A texture state, updates LRU frame, and increments `texture_binds` only when the bound texture changes.

- [ ] **Step 7: Run pure tests**

Compile `r_xbox_texture.c` with `DP_XBOX_RENDERER_TEST` and execute the layout/format/swizzle tests.

- [ ] **Step 8: Commit**

```bash
git add r_textures.h r_xbox_texture.h r_xbox_texture.c \
  r_xbox_internal.h r_xbox_backend.c tests/test_xbox_renderer_pure.c
git commit -m "render: add bounded NV2A texture manager"
```

---

### Task 6: Add Precompiled Vertex Programs and Register-Combiner Recipes

**Files:**
- Create: `r_xbox_program.h`
- Create: `r_xbox_program.c`
- Create: `xbox/shaders/xbox_2d.vs.cg`
- Create: `xbox/shaders/xbox_generic.vs.cg`
- Create: `xbox/shaders/xbox_world.vs.cg`
- Create: `xbox/shaders/xbox_model.vs.cg`
- Create: `xbox/shaders/xbox_billboard.vs.cg`
- Create: `xbox/shaders/xbox_dot3.vs.cg`
- Create: `xbox/shaders/xbox_solid.ps.cg`
- Create: `xbox/shaders/xbox_textured.ps.cg`
- Create: `xbox/shaders/xbox_lightmap.ps.cg`
- Create: `xbox/shaders/xbox_alpha.ps.cg`
- Create: `xbox/shaders/xbox_additive.ps.cg`
- Create: `xbox/shaders/xbox_fog.ps.cg`
- Create: `xbox/shaders/xbox_dot3.ps.cg`
- Create: `xbox/shaders/xbox_cubemap.ps.cg`
- Modify: `xbox/game/Makefile`
- Modify: `tests/test_xbox_renderer_contract.py`

**Interfaces:**
- Produces: `r_xbox_program_id_t`, `r_xbox_combiner_id_t`, `R_Xbox_ProgramsInit()`, `R_Xbox_ProgramsShutdown()`, `R_Xbox_SelectProgram()`, `R_Xbox_SelectCombiner()`, and constant upload functions.

- [ ] **Step 1: Add shader-source contract tests**

Require every mandatory shader source and generated `.inl` target name. Assert the Makefile defines `SHADER_OBJS` from `xbox/shaders/*.inl` and makes production sources depend on them.

- [ ] **Step 2: Define bounded program identifiers**

```c
typedef enum r_xbox_program_id_e
{
    R_XBOX_PROGRAM_2D,
    R_XBOX_PROGRAM_GENERIC,
    R_XBOX_PROGRAM_WORLD,
    R_XBOX_PROGRAM_MODEL,
    R_XBOX_PROGRAM_BILLBOARD,
    R_XBOX_PROGRAM_DOT3,
    R_XBOX_PROGRAM_COUNT
} r_xbox_program_id_t;

typedef enum r_xbox_combiner_id_e
{
    R_XBOX_COMBINER_SOLID,
    R_XBOX_COMBINER_TEXTURE_COLOR,
    R_XBOX_COMBINER_BASE_LIGHTMAP,
    R_XBOX_COMBINER_ALPHA_TEST,
    R_XBOX_COMBINER_ALPHA_BLEND,
    R_XBOX_COMBINER_ADDITIVE,
    R_XBOX_COMBINER_MODULATED_ADDITIVE,
    R_XBOX_COMBINER_FOG,
    R_XBOX_COMBINER_DOT3,
    R_XBOX_COMBINER_CUBEMAP,
    R_XBOX_COMBINER_FALLBACK,
    R_XBOX_COMBINER_COUNT
} r_xbox_combiner_id_t;
```

- [ ] **Step 3: Add nxdk shader generation**

Follow the pinned nxdk sample convention: `.vs.cg` / `.ps.cg` source generates `.inl`, and `SHADER_OBJS` lists every output. Include generated programs only from `r_xbox_program.c`.

- [ ] **Step 4: Implement upload and selection**

Upload vertex programs once at initialization. Program/combiner selection validates IDs, writes only changed state, and increments `state_changes`. Missing mandatory generated code makes `R_Xbox_ProgramsInit()` fail; there is no dummy success path.

- [ ] **Step 5: Define constant layout**

Use stable named slots for model, view, projection, model-view-projection, entity color, fog, light direction/color, and texture transforms. Add compile-time assertions that CPU arrays match four-float constant boundaries.

- [ ] **Step 6: Run source-contract checks**

```bash
python3 -m unittest tests.test_xbox_renderer_contract -v
```

Expected: shader inventory and Makefile dependency checks pass.

- [ ] **Step 7: Commit**

```bash
git add r_xbox_program.h r_xbox_program.c xbox/shaders \
  xbox/game/Makefile tests/test_xbox_renderer_contract.py
git commit -m "render: add fixed NV2A program library"
```

---

### Task 7: Implement Material Planning and Route DarkPlaces Shader Setup to Xbox Recipes

**Files:**
- Create: `r_xbox_material.h`
- Create: `r_xbox_material.c`
- Modify: `gl_rmain.c`
- Modify: `r_shadow.c`
- Modify: `tests/test_xbox_renderer_pure.c`

**Interfaces:**
- Produces: `r_xbox_material_request_t`, `r_xbox_material_plan_t`, `R_Xbox_PlanMaterial()`, `R_Xbox_ApplyMaterialPass()`, `R_Xbox_SetupSurfaceMaterial()`, and `R_Xbox_SetupGenericMaterial()`.

- [ ] **Step 1: Write table-driven material tests**

Each case supplies shader mode, permutation bits, material flags, blend factors, texture presence, and tier. Verify exact plan classification and pass count for:

- solid;
- base texture × color;
- base + lightmap;
- vertex color;
- alpha test;
- alpha blend;
- additive;
- glow multipass;
- fog;
- DOT3;
- cubemap approximation;
- water approximation;
- disabled deferred/shadow-map/postprocess;
- unknown permutation fallback.

- [ ] **Step 2: Define a bounded pass plan**

```c
#define R_XBOX_MAX_MATERIAL_PASSES 4

typedef enum r_xbox_material_class_e
{
    R_XBOX_MATERIAL_NATIVE,
    R_XBOX_MATERIAL_MULTIPASS,
    R_XBOX_MATERIAL_APPROXIMATE,
    R_XBOX_MATERIAL_DISABLED
} r_xbox_material_class_t;

typedef struct r_xbox_material_pass_s
{
    r_xbox_program_id_t program;
    r_xbox_combiner_id_t combiner;
    uint8_t texture_units[4];
    uint8_t texture_count;
    int blend_src, blend_dst;
    qbool depth_test, depth_write, alpha_test;
} r_xbox_material_pass_t;

typedef struct r_xbox_material_plan_s
{
    r_xbox_material_class_t classification;
    uint32_t fallback_reason;
    uint8_t pass_count;
    r_xbox_material_pass_t passes[R_XBOX_MAX_MATERIAL_PASSES];
} r_xbox_material_plan_t;
```

- [ ] **Step 3: Route `R_SetupShader_Surface`**

At the top of the existing function in `gl_rmain.c`:

```c
if (vid.renderpath == RENDERPATH_XBOX)
{
    R_Xbox_SetupSurfaceMaterial(
        rtlightambient, rtlightdiffuse, rtlightspecular,
        rsurfacepass, texturenumsurfaces, texturesurfacelist,
        surfacewaterplane, notrippy, ui);
    return;
}
```

Apply the same pattern to generic, depth, deferred, and postprocess setup functions. Xbox branches must return before any qgl/GLSL permutation code.

- [ ] **Step 4: Gate GL-only initialization and shadow paths**

Compile desktop GLSL tables/functions only for non-Xbox builds where feasible. In `r_shadow.c`, Xbox disables shadow-map FBO/query/readback code and routes bounded dynamic light draws to `R_Xbox_SetupSurfaceMaterial()`. Disabled paths increment stable reasons rather than invoking qgl.

- [ ] **Step 5: Emit one warning per fallback reason**

Use `R_Xbox_StatsWarnOnce()`. Every fallback increments per-frame totals; only the first occurrence per unique reason logs.

- [ ] **Step 6: Run pure planner tests**

Compile and execute `tests/test_xbox_renderer_pure.c` with `r_xbox_material.c` and program enums.

- [ ] **Step 7: Commit**

```bash
git add r_xbox_material.h r_xbox_material.c gl_rmain.c r_shadow.c \
  tests/test_xbox_renderer_pure.c
git commit -m "render: map DarkPlaces materials to NV2A recipes"
```

---

### Task 8: Make Existing 2D UI Code Render Through the Native Backend

**Files:**
- Create: `r_xbox_draw2d.h`
- Create: `r_xbox_draw2d.c`
- Modify: `gl_draw.c`
- Modify: `r_xbox_backend.c`
- Modify: `r_xbox_texture.c`
- Modify: `tests/test_xbox_renderer_pure.c`

**Interfaces:**
- Produces: `R_Xbox_Draw2DInit()`, `R_Xbox_Draw2DShutdown()`, `R_Xbox_Draw2DReady()`, `R_Xbox_DrawQuad()`, and bounded 2D batch flushing.
- Consumes: existing `Draw_*` cache/font/image logic and `R_Mesh_*` compatibility APIs.

- [ ] **Step 1: Add pure quad-batch tests**

Verify:

- solid and textured quad vertex generation;
- UV orientation;
- scissor clipping;
- zero-size rejection;
- batch flush at capacity;
- preservation of submission order across texture/blend changes.

- [ ] **Step 2: Keep `gl_draw.c` as high-level UI ownership**

Do not duplicate cachepic/font/loading/menu logic. Add an Xbox branch at the final quad emission boundary to call `R_Xbox_DrawQuad()`; desktop continues using its current path.

- [ ] **Step 3: Implement one bounded 2D batch**

Use a fixed maximum of 2048 quads per flush. Vertex layout is position2/3, color4ub, texcoord2. State changes flush the current batch. Use the 2D program and texture-color/solid combiners.

- [ ] **Step 4: Make 2D readiness mandatory**

`R_Xbox_Draw2DInit()` creates/checks white, black, missing, and font-compatible textures and confirms program/combiner availability. Failure prevents `cl_available = true`.

- [ ] **Step 5: Support engine UI requirements**

Cover solid fill, alpha/color modulation, texture quads, scissor, console text/background, loading screens, menus, HUD images, and controller graphics menu. Postprocess/font blur/outline requests use documented approximations or are disabled with counters.

- [ ] **Step 6: Run pure quad tests**

Use the host pure-test command with `r_xbox_draw2d.c`.

- [ ] **Step 7: Commit**

```bash
git add r_xbox_draw2d.h r_xbox_draw2d.c gl_draw.c \
  r_xbox_backend.c r_xbox_texture.c tests/test_xbox_renderer_pure.c
git commit -m "render: add native Xbox menu and HUD drawing"
```

---

### Task 9: Render Q3 BSP Worlds, Lightmaps, Alpha, Sky, and Fog

**Files:**
- Create: `r_xbox_world.h`
- Create: `r_xbox_world.c`
- Modify: `gl_rsurf.c`
- Modify: `r_sky.c`
- Modify: `model_brush.c`
- Modify: `tests/test_xbox_renderer_pure.c`

**Interfaces:**
- Produces: `R_Xbox_WorldInit()`, `R_Xbox_WorldShutdown()`, `R_Xbox_WorldBeginBatch()`, `R_Xbox_WorldDrawBatch()`, and `R_Xbox_WorldClassifySurface()`.

- [ ] **Step 1: Add world-classification tests**

Construct synthetic material/surface descriptors and verify classification for:

- opaque base;
- base + lightmap;
- vertex-lit;
- alpha-tested;
- alpha-blended;
- additive;
- sky;
- fogged;
- unsupported Q3 shader directive fallback;
- collision-only/debug surface exclusion.

- [ ] **Step 2: Reuse existing visibility and batching**

Keep PVS, frustum, surface lists, batch arrays, and model-buffer offsets from `gl_rsurf.c`/`model_brush.c`. Add Xbox hooks only where a pass plan, texture/lightmap pair, or buffer submission is selected.

- [ ] **Step 3: Implement world batch keys**

Key by recipe, base texture, lightmap texture, blend/depth policy, vertex/index buffer, and entity transform. Flush on key changes or ring limits.

- [ ] **Step 4: Implement required passes**

Support:

- base texture × vertex/entity color;
- base × lightmap in one pass where recipe permits;
- base then lightmap multipass fallback;
- alpha test;
- alpha blend;
- additive;
- fog;
- sky geometry/texture;
- brush submodels and movers.

- [ ] **Step 5: Handle unsupported directives deterministically**

Use base texture/fullbright fallback. Missing content uses the diagnostic checker texture. Never draw collision-only surfaces unless the existing debug cvar requests them.

- [ ] **Step 6: Run world-classification tests**

Compile pure world classification with the host harness.

- [ ] **Step 7: Commit**

```bash
git add r_xbox_world.h r_xbox_world.c gl_rsurf.c r_sky.c \
  model_brush.c tests/test_xbox_renderer_pure.c
git commit -m "render: add native Xbox BSP world rendering"
```

---

### Task 10: Render Models and Gameplay Effects with Visible Fallbacks

**Files:**
- Create: `r_xbox_models.h`
- Create: `r_xbox_models.c`
- Modify: `model_alias.c`
- Modify: `r_sprites.c`
- Modify: `cl_particles.c`
- Modify: `r_lightning.c`
- Modify: `r_explosion.c`
- Modify: `r_shadow.c`
- Modify: `tests/test_xbox_renderer_pure.c`

**Interfaces:**
- Produces: `R_Xbox_ModelsInit()`, `R_Xbox_ModelsShutdown()`, `R_Xbox_PrepareModelStreams()`, `R_Xbox_DrawModelBatch()`, `R_Xbox_DrawBillboardBatch()`, and gameplay-visibility fallback rules.

- [ ] **Step 1: Add model/effect classification tests**

Cover:

- opaque player/model;
- alpha entity;
- fullbright pickup/projectile;
- colormapped player;
- view weapon;
- sprite;
- particle;
- beam/lightning;
- decal;
- dynamic-light contribution;
- unsupported cosmetic material on a gameplay-critical entity.

The final case must choose a visible fullbright/base-texture fallback, never disabled.

- [ ] **Step 2: Use existing CPU animation outputs**

Consume existing interpolated/CPU-skinned vertex, normal, color, and texcoord arrays. Upload dynamic outputs to the vertex ring. Do not add GPU skinning.

- [ ] **Step 3: Implement model batches**

Use generic/model programs and material plans for players, bots, view weapons, projectiles, pickups, and brush entities. Preserve entity color, alpha, fullbright, and simple lighting.

- [ ] **Step 4: Implement billboard/effect batches**

Use one billboard program for sprites/particles and appropriate generic geometry for beams, lightning, explosions, and decals. Respect depth and blend policy.

- [ ] **Step 5: Gate unsupported shadow techniques**

Stencil model shadows may use the supported stencil path only if the current depth/stencil target provides it; otherwise classify as disabled/approximate. Shadow maps remain disabled.

- [ ] **Step 6: Run pure classification tests**

Compile and run the host harness.

- [ ] **Step 7: Commit**

```bash
git add r_xbox_models.h r_xbox_models.c model_alias.c r_sprites.c \
  cl_particles.c r_lightning.c r_explosion.c r_shadow.c \
  tests/test_xbox_renderer_pure.c
git commit -m "render: add Xbox models and gameplay effects"
```

---

### Task 11: Add Bounded Dynamic Lighting, DOT3, Water, and Reflection Approximations

**Files:**
- Modify: `r_xbox_material.h`
- Modify: `r_xbox_material.c`
- Modify: `r_xbox_program.c`
- Modify: `r_xbox_world.c`
- Modify: `r_xbox_models.c`
- Modify: `r_shadow.c`
- Modify: `cl_graphics_menu.c`
- Modify: `tests/test_xbox_renderer_pure.c`

**Interfaces:**
- Extends material planner with quality tiers and supported controls.
- Produces: `R_Xbox_SetQualityTier()`, `R_Xbox_GetQualityTier()`, and explicit feature-support queries used by the graphics menu.

- [ ] **Step 1: Add quality-tier tests**

Define:

```c
typedef enum r_xbox_quality_tier_e
{
    R_XBOX_QUALITY_LOW,
    R_XBOX_QUALITY_MEDIUM,
    R_XBOX_QUALITY_HIGH
} r_xbox_quality_tier_t;
```

Verify exact treatment of dynamic lights, DOT3, water, cubemap reflections, stencil shadows, particles, and texture precision at each tier.

- [ ] **Step 2: Implement bounded dynamic-light passes**

Apply a configured maximum number of dynamic lights per surface/entity based on tier. Select nearest/influential lights deterministically. Count omitted lights.

- [ ] **Step 3: Implement DOT3 when tangent data exists**

Use the mandatory DOT3 program/combiner. If normal/tangent maps or vectors are absent, use the base/lightmap or directional-light approximation.

- [ ] **Step 4: Implement water and reflection approximations**

Water uses animated texture coordinates/base texture/alpha; it does not require screen-space refraction. Cubemap reflection uses the bounded cubemap recipe when texture memory permits, otherwise base + reflect-mask approximation.

- [ ] **Step 5: Connect graphics controls to actual support**

The controller graphics menu must mark disabled features unavailable or show their Xbox approximation/tier. Do not expose bloom, deferred lighting, motion blur, or shadow maps as operational.

- [ ] **Step 6: Run quality/material tests**

Compile and execute the host harness.

- [ ] **Step 7: Commit**

```bash
git add r_xbox_material.h r_xbox_material.c r_xbox_program.c \
  r_xbox_world.c r_xbox_models.c r_shadow.c cl_graphics_menu.c \
  tests/test_xbox_renderer_pure.c
git commit -m "render: add bounded Xbox lighting and effects"
```

---

### Task 12: Cut the Production Target Over from Bootstrap to Native Renderer

**Files:**
- Modify: `xbox/game/sources.mk`
- Modify: `xbox/game/Makefile`
- Modify: `xbox/game/profile.h`
- Modify: `vid_xbox.c`
- Modify: `xbox/game/README.md`
- Modify: `tools/xbox/audit_game_link.py`
- Modify: `tools/xbox/audit_renderer_sources.py`
- Modify: `tests/test_xbox_renderer_contract.py`

**Interfaces:**
- Makes `XBOX_RENDERER=native` the production default.
- Keeps `XBOX_RENDERER=bootstrap` as an explicit diagnostic-only opt-in.
- Produces final initialization stage markers and renderer identity output.

- [ ] **Step 1: Extend contract tests for final selection**

Require:

- default `XBOX_RENDERER ?= native`;
- native list excludes bootstrap, `gl_backend.c`, and `gl_textures.c`;
- exactly one definition owner for every `VID_*`, `R_Mesh_*`, and `R_LoadTexture*` family;
- `DP_XBOX_CAP_RENDERER` remains 0 until runtime evidence changes it in a later evidence commit;
- source identity names render path, quality tier, depth format, texture budget, ring sizes, and enabled approximations.

- [ ] **Step 2: Make native initialization atomic**

`R_Xbox_Init()` executes:

```text
backend/device
-> targets
-> rings
-> textures/defaults
-> programs/combiners
-> material planner
-> 2D
-> world
-> models
```

On any failure it calls `R_Xbox_Shutdown()` in reverse order and returns false. Only the caller in `VID_InitMode()` sets `cl_available = true`.

- [ ] **Step 3: Add exact stage markers**

Emit once:

```text
XBOX_RENDERER_VIDEO_READY
XBOX_RENDERER_BACKEND_READY
XBOX_RENDERER_TEXTURES_READY
XBOX_RENDERER_PROGRAMS_READY
XBOX_RENDERER_2D_READY
XBOX_RENDERER_WORLD_READY
XBOX_RENDERER_MODELS_READY
XBOX_RENDERER_CLIENT_READY
```

Failures emit `XBOX_RENDERER_FAIL stage=<name> code=<stable-code>`.

- [ ] **Step 4: Update link/source audits**

`audit_game_link.py` rejects any native game link map containing qgl entry points, GL loader libraries, `vid_xbox_bootstrap`, `gl_backend`, or `gl_textures`. It requires every `r_xbox_*` object and generated shader object.

- [ ] **Step 5: Update build documentation honestly**

Document source readiness and build command, but keep compile/xemu/hardware claims absent until those gates are executed. State that audio remains separate and the game is not fully playable until audio/content/runtime validation are complete.

- [ ] **Step 6: Run source-only contract checks**

```bash
python3 -m unittest tests.test_xbox_renderer_contract -v
python3 tools/xbox/audit_renderer_sources.py \
  --root . \
  --manifest xbox/game/sources.mk \
  --mode native
```

Expected: PASS. These checks establish source ownership only.

- [ ] **Step 7: Commit**

```bash
git add xbox/game/sources.mk xbox/game/Makefile xbox/game/profile.h \
  vid_xbox.c xbox/game/README.md tools/xbox/audit_game_link.py \
  tools/xbox/audit_renderer_sources.py tests/test_xbox_renderer_contract.py
git commit -m "render: select the production NV2A renderer"
```

---

### Task 13: Execute the Deferred Compile and Runtime Verification Gates

**Files:**
- Create: `.github/workflows/xbox-renderer.yml`
- Create: `evidence/xbox-renderer/README.md`
- Modify only when failures identify real defects: renderer implementation files from Tasks 1–12.

**Interfaces:**
- Consumes the completed source implementation.
- Produces separate evidence for compile, link, package, present, 2D, world, model, and route gates.

- [ ] **Step 1: Cross-compile the production target**

```bash
make -C xbox/game \
  NXDK_DIR=/absolute/path/to/nxdk \
  CONTENT_DIR=/absolute/path/to/prepared-nexuiz \
  XBOX_RENDERER=native \
  V=1
```

Expected: XBE, ISO, link map, generated shaders, and no desktop GL symbols.

- [ ] **Step 2: Audit the link map**

```bash
python3 tools/xbox/audit_game_link.py \
  --map xbox/game/build/nexuiz-xbox.map \
  --renderer native
```

Expected: all native modules present; prohibited GL/bootstrap owners absent.

- [ ] **Step 3: Run xemu gates in order**

Do not skip ahead:

1. video init and clear/present;
2. 2D console/menu;
3. one textured indexed mesh;
4. one pinned BSP;
5. models/effects;
6. automatic demo route.

Capture stage markers, logs, screenshots, renderer counters, and memory high water separately.

- [ ] **Step 4: Run stock-memory hardware gates**

Repeat the same ordered gates on a 64 MiB console. Do not use 128 MiB results as release acceptance.

- [ ] **Step 5: Change runtime capability only after evidence**

After native renderer initialization, visible 2D, BSP, and required model/effect gates pass in xemu and hardware, update `DP_XBOX_CAP_RENDERER` in a dedicated evidence-backed commit. Do not combine that claim with unrelated fixes.

- [ ] **Step 6: Commit workflow/evidence metadata**

```bash
git add .github/workflows/xbox-renderer.yml evidence/xbox-renderer
git commit -m "ci: validate the native Xbox renderer gates"
```

---

## Plan Self-Review

- **Spec coverage:** Tasks 1–12 cover render-path identity, video/present, state, buffers, textures, fixed programs, material classification, 2D, BSP/world, models/effects, advanced approximations, diagnostics, memory ceilings, failure policy, and source cutover. Task 13 covers the deliberately deferred evidence gates.
- **No competing renderer:** Native mode excludes `gl_backend.c`, `gl_textures.c`, and bootstrap video while retaining high-level traversal modules with explicit Xbox material branches.
- **Type consistency:** Lifecycle, stats, ring, program, combiner, material-plan, quality-tier, world, model, and 2D interfaces are defined before later tasks consume them.
- **Capability honesty:** Bootstrap remains the default during Tasks 1–11; Task 12 changes the production default to native. The native compiler definition is mode-specific, and `DP_XBOX_CAP_RENDERER` stays false until runtime gates pass.
- **Subsystem isolation:** Audio, LAN sessions, and content licensing remain outside this plan.
