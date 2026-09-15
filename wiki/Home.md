# DarkPlaces Original Xbox Port

This wiki is the source of truth for preparing DarkPlaces and selected Nexuiz content for the original Xbox.

## Objective

Produce a deterministic, continuously looping 3D stress world that transitions through mixed workloads without returning to a menu or separate microtests. The camera should move through texture-heavy, geometry-heavy, alpha/overdraw-heavy, particle-heavy, math-heavy, animated, and combined scenes. The same content and path must run in xemu and on a standard 64 MB retail Xbox.

## Current reality

The repository is a fresh fork of modern DarkPlaces. Its renderer supports OpenGL 3.2 and GLES2, while nxdk provides native NV2A graphics facilities rather than a compatible implementation of those DarkPlaces render paths. The port therefore needs an explicit `RENDERPATH_XBOX`, a reduced feature policy, and careful 64 MB asset management.

## Navigation

- [Port goals and scope](Port-Goals-and-Scope)
- [Port design](Original-Xbox-Port-Design)
- [Architecture](Architecture)
- [Build and toolchain](Build-and-Toolchain)
- [Renderer strategy](Renderer-Strategy)
- [Feature support matrix](Feature-Support-Matrix)
- [Memory budget](Memory-Budget)
- [Nexuiz stress world](Nexuiz-Stress-World)
- [Validation and telemetry](Validation-and-Telemetry)
- [Porting roadmap](Porting-Roadmap)
- [Implementation plan](Implementation-Plan)
- [Issue map](Issue-Map)
- [Contribution workflow](Contribution-Workflow)
- [Licensing and content](Licensing-and-Content)

The repository stores these pages under `wiki/`. A manual workflow publishes the directory to the GitHub Wiki once the Wiki repository has been initialized.
