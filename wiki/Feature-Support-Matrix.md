# Feature Support Matrix

This matrix states required policy, **not proof of implementation**. [Option B](Playable-Game-and-LAN) supersedes the benchmark-only scope. The current native executables remain diagnostics; update execution status only with evidence.

| System | First release policy | Validation |
|---|---|---|
| Desktop SDL renderer | Preserve | Existing `sdl-release` CI |
| Xbox video | Tested mode selection compatible with attached output; no assumed 480p prerequisite | xemu + retail hardware |
| Generic textured mesh | Native | reference capture |
| World/material texture resolution on stock memory | Deliberate reduced-resolution fallback: canonical staging generates a content-addressed stored override PK3 for every effective TGA above 512 pixels on either axis. External Q3 lightmaps use a 128x128 ceiling and the Xbox classic loader streams their decode/conversion/upload one image at a time; resulting GPU lightmaps do not use world picmip. All profiles use the overrides so one XISO remains canonical. `retail64`/`xemu64` also enforce `gl_picmip >= 2`; diagnostic `dev128` preserves the saved runtime choice. Originals remain immutable. | deterministic converter/loader fixtures + content identity + controlled visual comparison + stock-memory high-water evidence |
| BGRA texture input on classic pbGL path | Profiled compatibility conversion with a checked 16 MiB transient staging ceiling; source buffers remain engine-owned and unchanged. `retail64`/`xemu64` use native packed RGBA4 storage to halve residency; diagnostic `dev128` retains RGBA8. Four-bit color/alpha is a deliberate stock-memory approximation. | adapter fixture + GL error checks + native color/alpha chart |
| `glArrayElement` driver-test path | Disabled; production remains on pbGL `glDrawElements`, and forcing `gl_mesh_testarrayelement` is a deliberate no-op fallback | link audit + native mesh capture |
| 2D console/menu | Native | text and UI screenshots |
| Q3 BSP/PVS | Required | full pinned map inventory, not only a demo |
| Lightmaps | Required | static comparison |
| Alpha test/blend/additive | Required | stress-zone markers |
| Fog | Required, approximation allowed | deterministic capture |
| Sky | Required, simplified allowed | map comparison |
| MD3/required Nexuiz models | Required after audit | animation capture |
| Skeletal formats used anywhere in pinned game | Required | full-game content/animation audit |
| Particles/sprites/decals | Required | count and overdraw zones |
| Dynamic lights | Required subset | controlled scene |
| DOT3 normal/gloss material layers | Diffuse/lightmap fallback on `retail64` and `xemu64`: optional normal and gloss assets are not loaded under those profiles. `dev128` diagnostically honors the saved normal/gloss renderer controls. A bounded 64 MiB implementation remains required before enabling the layers on retail. | profile trace + controlled scene + stock-memory high-water evidence |
| Cubemap reflections | Desired | fallback documented |
| Water/refraction | Approximate or multipass | comparison + timing |
| Realtime shadows | Native/multipass or explicit cosmetic approximation; required game visibility preserved | coverage and cost report |
| Deferred rendering | Disabled | compile-time exclusion |
| HDR/bloom/FXAA | Individually audit; unsupported native settings must be explicit, no blanket capability claim | native recipe or visible unsupported policy |
| Video capture/playback | Disabled | build audit |
| ODE physics | Retain required game behavior if any pinned map/mode depends on it; otherwise exclude | full-game content audit |
| Dynamic library loading | Disabled | link audit |
| Curl/http downloads | Disabled initially | network audit |
| Offline game/client/server/VM/bots | Required | complete matches and campaign paths, #35 |
| LAN host/join/discovery/direct address | Required | two-way native sessions and published limits, #36 |
| Internet browsing/advertising/NAT services | Excluded from Option B | no unsolicited external service traffic |
| Settings and supported progression persistence | Required | save/relaunch and failed-write recovery |
| Controller input | Required for controls | hardware test |
| Audio | Required for playable game; muted/no-audio benchmarking remains an explicit separate profile | positional effects, music, underrun/restart tests |
| Runtime PNG/JPEG decoding | Bring-up only where affordable | memory trace |
| Preconverted asset cache | Required for final workload | cache hit report |

Use `Native`, `Multipass`, `Approximate`, `Disabled`, and `Deferred` consistently in issue/PR descriptions.
