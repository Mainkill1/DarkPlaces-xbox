# Port Goals and Scope

## Primary product

The primary product is an original Xbox executable that automatically loads a large mixed world, follows a deterministic camera path, records performance data, and loops indefinitely.

This is closer to a period-correct 3DMark/FurMark world than a complete game port. Nexuiz and DarkPlaces are valuable because they already provide BSP loading, visibility, materials, models, particles, QuakeC, demos, and content capable of producing varied workloads.

## Baseline target

- Original Xbox with 64 MB unified memory.
- nxdk open-source toolchain.
- 480p-first output; other modes are optional.
- xemu for rapid development and automated runs.
- Real hardware for acceptance and timing/memory validation.
- Local content from XISO or HDD layout.
- Deterministic playback and repeatable settings.

## Required workload zones

The final world must transition continuously through:

1. Normal baseline geometry.
2. Large BSP view and visibility pressure.
3. Texture-heavy area with frequent material changes and mip transitions.
4. Alpha vegetation/fur/shell area with high overdraw.
5. Particle, sprite, decal, smoke, and additive-light area.
6. Math-heavy animated/deformed geometry.
7. Model/animation crowd or machinery area.
8. Dynamic-light, DOT3/normal-map, reflection, and multipass area.
9. Final combined section with several systems active simultaneously.
10. Recovery section proving resources are released/reused before the loop repeats.

## Explicitly deferred

- Feature-complete online Nexuiz.
- Perfect visual parity with current desktop DarkPlaces.
- Modern shadow maps, deferred rendering, HDR/bloom, and arbitrary GLSL permutations.
- Every game/mod supported by DarkPlaces.
- 720p/1080i as baseline.
- Dependence on upgraded 128 MB consoles.
- Proprietary Xbox SDK tooling or redistributable retail data.

## Acceptance definition

The first meaningful release completes the full camera loop for at least one hour on xemu and a standard retail Xbox without a crash, unbounded memory growth, corrupted rendering state, or result-file failure. Visual fallbacks are acceptable only when documented in the feature matrix and stable across loops.
