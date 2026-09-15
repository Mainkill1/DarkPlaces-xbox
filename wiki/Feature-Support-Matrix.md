# Feature Support Matrix

This matrix is a policy document. Update it whenever a PR changes Xbox behavior.

| System | First release policy | Validation |
|---|---|---|
| Desktop SDL renderer | Preserve | Existing `sdl-release` CI |
| Xbox video | 480p-first, fixed mode | xemu + retail hardware |
| Generic textured mesh | Native | reference capture |
| 2D console/menu | Native | text and UI screenshots |
| Q3 BSP/PVS | Required | selected Nexuiz map |
| Lightmaps | Required | static comparison |
| Alpha test/blend/additive | Required | stress-zone markers |
| Fog | Required, approximation allowed | deterministic capture |
| Sky | Required, simplified allowed | map comparison |
| MD3/required Nexuiz models | Required after audit | animation capture |
| Skeletal formats not used by target | Deferred | content audit |
| Particles/sprites/decals | Required | count and overdraw zones |
| Dynamic lights | Required subset | controlled scene |
| DOT3/normal mapping | Required subset | controlled scene |
| Cubemap reflections | Desired | fallback documented |
| Water/refraction | Approximate or multipass | comparison + timing |
| Realtime shadows | Disabled initially | fallback counter |
| Deferred rendering | Disabled | compile-time exclusion |
| HDR/bloom/FXAA | Disabled | compile-time exclusion |
| Video capture/playback | Disabled | build audit |
| ODE physics | Disabled unless target content proves need | content audit |
| Dynamic library loading | Disabled | link audit |
| Curl/http downloads | Disabled initially | network audit |
| Multiplayer networking | Deferred | not required for benchmark |
| Controller input | Required for controls | hardware test |
| Audio | Optional for benchmark, backend planned | no-audio mode must work |
| Runtime PNG/JPEG decoding | Bring-up only where affordable | memory trace |
| Preconverted asset cache | Required for final workload | cache hit report |

Use `Native`, `Multipass`, `Approximate`, `Disabled`, and `Deferred` consistently in issue/PR descriptions.
