# Controller graphics settings

Branch: `port/nexuiz-graphics-menu`, based on autoplay PR #33. The pending original
smoke branch is unchanged. This implements an engine-owned operations/graphics
panel, not another renderer or a claim of a runnable Xbox engine.

## Default and user choice

Automatic FPS-based quality reduction defaults **OFF** (`cl_minfps 0`). Both the
engine default and the generated `xbox-benchmark.cfg` say off; the Xbox/attract
boot path also clears any inherited game-profile minimum-FPS setting. Saved,
explicit user preferences load afterward and may turn adaptation on.

The switch uses the real `cl_minfps` state, not a separate UI-only boolean. ON
restores an effective 0.25..1 quality interval and the remembered target (initially
60 FPS). OFF sets `cl_minfps` to zero; the existing renderer resets its adaptive
factor on the next update. Turning it off does not disable manually selected
particles, lights, shadows, or other effects. The target is independent of the
frame cap. Timedemo retains the engine's normal suppression of adaptation
(`cl_minfps_force 0`); enabling the option is primarily for ordinary playback.

The generated defaults are loaded only at boot, not every demo restart. Returning
to the loop therefore retains menu edits. Each demo start logs `XBOX_GRAPHICS_PROFILE`
and the selected values; adaptation is labelled `adaptive`, not a fixed-work
benchmark. This is provenance logging, not a complete performance scorer.

## Controller operation

After a fresh button leaves autoplay, the operations panel offers **Graphics
settings**, **Restart demo loop**, and **Nexuiz game menu**. The panel requires no
particular version of Nexuiz's `menu.dat`.

| Input | Operation |
|---|---|
| D-pad / left stick up/down | Browse, including automatic page scrolling |
| D-pad / left stick left/right | Adjust the selected graphics setting |
| A | Enter, toggle, or execute the selected action |
| B / Back | Back to the operations panel; from there open the game menu |
| Start in graphics | Back; never silently restart while editing |
| Start at operations/game menu | Restart the stopped demo loop |
| Y in a menu | Open the operations panel |

The existing controller adapter retains automatic device selection and hotplug.
Changing menu pages resets the input gate: held takeover/navigation buttons must
be released. Engine key bookkeeping happens before menu consumption so synthetic
releases also clear button-repeat state. Gameplay inputs do not leak into the panel.

## Available settings

The scrollable panel exposes automatic quality and its target, frame cap, VSync,
texture reduction, anisotropic filtering, particles and their count multiplier,
decals, coronas, flashblend, dynamic/world lighting and shadows, bloom, water,
sky and gamma. Values are changed through actual engine cvars. Missing/read-only
cvars are displayed as unavailable; anisotropy is bounded to the reported backend
limit. The UI names dependency requirements, such as Flashblend overriding some
real-time dynamic lighting behavior.

A menu setting does not implement an unsupported NV2A effect. These settings have
existing desktop render paths; the future native renderer must implement or
explicitly reject its unsupported paths. Resolution/refresh/MSAA are deliberately
left to the existing game's video menu and future native mode enumeration, not
populated with unverified Original Xbox modes.

Texture reduction needs **Apply texture changes** (queues `r_restart`) or a later
resource reload before all existing textures use it. Other controls update the
session cvars immediately; a renderer may apply them on its next frame. Read the
on-screen help and pending-reload indication rather than assuming every setting
has the same resource lifetime.

## Save and reload

**Save graphics preferences** writes only this panel's numeric settings to
`xbox-graphics.cfg` in the engine's writable game/user directory. It checks opening,
full-length writing, and close success. Short writes are marked for removal rather
than reported as saved. Read-only storage or I/O errors produce an explicit
**Save FAILED; session-only** message. Saving does not guarantee survival of power
loss or an atomic replacement of an old file.

The startup order is:

```
normal game startup -> generated default-OFF profile -> saved graphics preferences
 -> automatic demo start
```

With no saved file, fixed quality remains the default. Native persistence still
requires the Xbox filesystem implementation; this branch does not claim that
capability is already available in the smoke XBE.

## Implementation and validation

- `cl_graphics_menu.c/.h`: bounded table, cvars, panel rendering, key handling,
  pending texture reload and checked preference writes.
- `cl_attract.c`: panel entry, Start/Y routing, page-change input gate, startup
  preference ordering and per-demo settings logs.
- `cl_screen.c` / `keys.c`: real DrawQ and key-event integration; unchanged outside
  the opted-in profile except the intentional global default `cl_minfps 0`.
- `tools/xbox/autoplay_config.py`: default-OFF packaged profile.
- `tests/test_xbox_graphics.py`: default generation, real-source menu behavior,
  persistence failure cases and integration ordering. Renderer/filesystem/cvar
  services are test doubles, not physical-console evidence.

Run `python3 -m unittest discover -s tests -p 'test_*.py' -v`. The existing autoplay
workflow also requires real SDL virtual-controller tests and links the unchanged
native controller diagnostic. The desktop engine build remains the full compile/link
regression. A physical game/menu run and Xbox engine/NV2A integration are still open
under issues #23, #25 and #28.
