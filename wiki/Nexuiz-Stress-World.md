# Nexuiz Stress World

## Source strategy

Use DarkPlaces/Nexuiz as the content and behavior donor, but do not require the first Xbox build to run every Nexuiz feature. Select one world and one deterministic path, then implement the subset it needs.

The content audit must identify:

- map/BSP version and lumps;
- textures and source formats;
- shader/material scripts;
- model formats and animation paths;
- particle definitions;
- QuakeC dependencies;
- sounds/music;
- licenses and redistribution status;
- peak source and prepared asset sizes.

## Continuous workload design

The camera should never jump to a separate benchmark test. Workload zones are connected spatially and marked in telemetry:

| Marker | Zone |
|---|---|
| `BASELINE` | ordinary world rendering |
| `VISTA` | broad BSP visibility and geometry |
| `TEXTURE` | many materials, mips, and cache pressure |
| `ALPHA` | foliage/fur/shell layers and overdraw |
| `PARTICLE` | smoke, sparks, decals, additive sprites |
| `DEFORM` | CPU/vertex math and moving geometry |
| `ANIMATION` | crowds or machinery |
| `LIGHTING` | dynamic lights, normal/DOT3, reflections |
| `COMBINED` | several expensive systems together |
| `RECOVERY` | resource reuse/eviction verification |

## Deterministic camera

The final harness should support:

- fixed path duration and interpolation;
- fixed or recorded time step;
- fixed random seed;
- warm-up loop excluded from reported results;
- exact workload marker timestamps;
- automatic restart and loop counter;
- controller pause/restart/overlay controls that do not alter the measured path.

Existing DarkPlaces demo playback may be reused if it remains deterministic and content-independent enough. Otherwise add a small camera-spline format rather than bending network demo behavior beyond recognition.

## Stress scaling

Each zone should expose a controlled workload scalar in content or configuration: particle count, shell count, animated object count, visible model set, dynamic-light count, or material layers. This permits a heavy retail profile and an intentionally excessive emulator/profiling profile without maintaining separate worlds.
