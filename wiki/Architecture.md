# Architecture

## Guiding structure

Keep the DarkPlaces simulation, VFS, BSP/model loaders, material interpretation, particles, and demo/camera logic where practical. Replace platform and rendering boundaries explicitly.

```text
Nexuiz data / prepared Xbox asset cache
                    |
DarkPlaces VFS, game selection, QuakeC, demo/camera
                    |
World/model visibility and render queue construction
                    |
           RENDERPATH_XBOX
      +-------------+-------------+
      |             |             |
  NV2A mesh     texture/cache   state/material
  submission      manager        translation
      |             |             |
              nxdk / pbkit
                    |
              NV2A + 64 MB
```

## Platform modules

- `sys_xbox.c`: entry point, timing, logging, fatal errors, shutdown.
- `thread_xbox.c`: mutex/thread/condition behavior or documented single-thread fallback.
- `vid_xbox.c`: fixed video mode, controller/event pump, GPU startup, present.
- `snd_xbox.c`: SDL2 audio or native audio after an evidence-based choice.
- filesystem adaptations: drive roots, read-only content, writable config/results.
- `config_xbox.h`: one auditable feature policy, not scattered ad-hoc disables.

## Renderer boundary

Add `RENDERPATH_XBOX` rather than emulating OpenGL calls one by one without a capability model. Reuse high-level DarkPlaces batching and material decisions where they map cleanly, then translate a small supported material set to NV2A state, vertex programs, register combiners, and multipass draws.

The backend must own:

- frame/device lifecycle;
- dynamic/static vertex and index buffers;
- texture upload, swizzle/compression, mipmaps, and eviction;
- render targets/depth buffer;
- draw/state submission;
- supported shader/material recipes;
- fallback counters and diagnostics.

## Content path

Runtime decoding is useful for bring-up but should not define the final memory/performance path. A host-side converter should prebuild Xbox-ready texture and mesh caches while leaving source packages outside the repository unless their licenses are verified.

## Determinism

Benchmark mode owns the camera clock, random seed, quality profile, workload markers, and loop reset. Interactive controller input may pause, restart, toggle overlays, or quit, but cannot affect measured camera motion.
