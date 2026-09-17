# NV2A Renderer Task 2 Amendment

This amendment corrects one sequencing assumption in `2026-09-16-nv2a-renderer-implementation.md` and records the source-only Task 2 boundary.

## Correct `cl_available` semantics

DarkPlaces checks `cl_available` before it calls `VID_Init`. If an Xbox build defines it as false until video initialization completes, `Host_Init` selects dedicated/headless behavior and never executes the native client-video path.

For the production Xbox client:

```c
int cl_available = true;
```

means only that client support is compiled into the executable. It is not renderer evidence.

Native runtime readiness is tracked separately:

```text
xbox_video.runtime_ready == false
    before or after failed native video initialization

xbox_video.runtime_ready == true
    only after video mode, pbkit and the currently required backend stage initialize
```

Later renderer tasks extend the required initialization chain to targets, rings, textures, programs, materials, 2D, world and models before the production source cutover. `DP_XBOX_CAP_RENDERER` remains zero until the separate runtime-evidence gates pass.

## Task 2 source prepared

Task 2 source now provides:

- `vid_xbox.c` ownership of `XVideoSetMode`, `pb_init`, `pb_kill`, fixed mode metadata, normal controller input, attract-mode takeover, video cleanup and `VID_Finish`;
- `r_xbox_backend.c/.h` ownership of frame begin/end, back-buffer targeting, bounded GPU waits, presentation queuing, optional vblank pacing and statistics;
- removal of pre-`Host_Init` framebuffer initialization from `sys_xbox.c` so video ownership is not duplicated;
- bootstrap remaining the default renderer selection while subsequent native renderer modules are unfinished.

No compilation, test, XBE/ISO production, xemu run or hardware execution was performed for this source task, by owner direction.
