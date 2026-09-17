# DarkPlaces Original Xbox Port

This wiki is the source of truth for the playable Nexuiz Classic Original Xbox port, including offline play, LAN multiplayer and the continuous stress benchmark.

## Objective

Option B is approved: deliver a fully playable offline game plus LAN host/join, audio, persistence and controller menus. Retain a deterministic, continuously looping 3D stress world that transitions through mixed workloads without returning to a menu or separate microtests. The camera should move through texture-heavy, geometry-heavy, alpha/overdraw-heavy, particle-heavy, math-heavy, animated, and combined scenes. The same content and path must run in xemu and on a standard 64 MB retail Xbox.

## Current reality

PRs #31–#34 are merged. The user has shown the diagnostic foundation boot in xemu; that remains a diagnostic rather than game evidence.

The repository now has an integrated first game-build candidate under `xbox/classic/`, using a Nexuiz-era DarkPlaces revision and pbGL/PBKit/NV2A, plus initial Xbox controller/video/audio/network platform code. `xbox/release/` is the canonical dependency/content/build/package wrapper for that candidate. Its external inputs are exact-commit/hash locked and the complete Nexuiz 2.5.2 archive is staged from a durable verified source instead of expiring CI artifacts.

The modern `xbox/game/` direct `RENDERPATH_XBOX` backend remains in development and is not the first full integration target. The integrated candidate has not yet passed the full cross-build/runtime ladder, so source presence is not a claim that rendering, audio, gameplay, LAN or 64 MiB acceptance already works. The next major evidence gate is the first locked full build, followed by xemu bring-up.

The live implementation queue is the [master port epic](https://github.com/Mainkill1/DarkPlaces-xbox/issues/1) and its linked issues #2–#30 plus #35 (offline gameplay) and #36 (LAN). Wiki pages describe the durable design; issues own execution status and evidence.

## Navigation

- [Live port epic and issue queue](https://github.com/Mainkill1/DarkPlaces-xbox/issues/1)
- [Playable game and LAN — approved Option B](Playable-Game-and-LAN)
- [Port goals and scope](Port-Goals-and-Scope)
- [Port design](Original-Xbox-Port-Design)
- [Architecture](Architecture)
- [Build and toolchain](Build-and-Toolchain)
- [Renderer strategy](Renderer-Strategy)
- [Feature support matrix](Feature-Support-Matrix)
- [Memory budget](Memory-Budget)
- [Nexuiz stress world](Nexuiz-Stress-World)
- [Nexuiz integration preparation](Nexuiz-Integration-Preparation)
- [Autoplay and controller operation](Autoplay-and-Controller)
- [Validation and telemetry](Validation-and-Telemetry)
- [Porting roadmap](Porting-Roadmap)
- [Implementation plan](Implementation-Plan)
- [Issue map](Issue-Map)
- [Contribution workflow](Contribution-Workflow)
- [Licensing and content](Licensing-and-Content)
- [Controller graphics settings](Controller-Graphics-Settings)

## Publishing

The repository stores the canonical pages under `wiki/`. GitHub does not expose the separate `DarkPlaces-xbox.wiki` Git repository until a Home page has been created once from the repository Wiki tab. After that one-time initialization, run the **Publish repository wiki** workflow to synchronize this directory.
