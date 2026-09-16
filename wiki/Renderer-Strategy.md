# Renderer Strategy

## Option B coverage

The [playable-game contract](Playable-Game-and-LAN) requires coverage of the complete pinned Nexuiz game, not only the benchmark route. The bring-up ladder below is an implementation sequence, not a reduced release promise. Cosmetic approximations must preserve gameplay-critical visibility, actors, collision cues and HUD information.

## Why a new render path is required

Modern DarkPlaces exposes `RENDERPATH_GL32` and `RENDERPATH_GLES2`. Its material system selects many GLSL modes and permutations for generic drawing, lightmaps, model lighting, realtime lights, water, refraction, reflections, fog, skeletal transforms, shadows, and postprocessing.

The original Xbox NV2A does not run these GLSL programs directly. nxdk exposes native graphics facilities, vertex-program tooling, and register-combiner tooling. Therefore the port must not assume that nxdk SDL2 solves the renderer.

## Chosen direction

Introduce `RENDERPATH_XBOX` and implement a deliberately bounded NV2A backend.

The backend should consume high-level DarkPlaces mesh/material inputs where useful, but it should select from a small library of known Xbox recipes rather than attempting arbitrary GLSL translation at runtime.

## Bring-up ladder

1. Clear color/depth and present.
2. Untextured indexed triangles.
3. Textured mesh with transform.
4. Vertex color and alpha.
5. 2D orthographic drawing.
6. Static world surfaces.
7. Lightmapped world surfaces.
8. Alpha test, alpha blend, additive blend.
9. Fog and sky.
10. Animated models.
11. Particles/sprites/decals.
12. Dynamic light and DOT3 recipes.
13. Cubemap/reflection recipe.
14. Deliberate multipass fallbacks for combined materials.

Each rung must include a failure counter or visible diagnostic when unsupported state reaches the backend.

## Material policy

Every desktop feature falls into one of four categories:

- **Native:** maps directly to an NV2A recipe.
- **Multipass:** supported through two or more passes with documented cost.
- **Approximate:** visually reduced but stable.
- **Disabled:** excluded from the Xbox profile with an explicit reason.

The backend must never silently render a complex material as a random generic texture. Unsupported recipes use a deterministic fallback and increment a named counter.

## Non-goals for first release

- General GLSL compiler or translator.
- Deferred lighting.
- Modern shadow-map pipeline.
- Exact parity for modern post-processing; individual controls require a supported native recipe or an explicit unsupported state.
- Unlimited material permutations.
- Visual parity with desktop DarkPlaces.

## Architectural warning

A giant OpenGL shim that reproduces all desktop entry points may appear quick at first but hides capability mismatches and makes performance attribution difficult. Small compatibility helpers are acceptable; the port should still expose a first-class Xbox render path and measurable NV2A operations.
