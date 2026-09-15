# Agent Rules for the Original Xbox Port

Read `PORTING.md`, `wiki/Home.md`, and the [master port epic](https://github.com/Mainkill1/DarkPlaces-xbox/issues/1) before changing code.

## Hard rules

1. The target is a deterministic Nexuiz-derived stress world on a standard 64 MB original Xbox.
2. Do not claim “Xbox support” from a compile-only result. State the exact gate reached: compiled, linked, XBE produced, booted, frame presented, map loaded, complete route finished, or soak passed.
3. Preserve the desktop `make sdl-release` build.
4. Prefer new Xbox platform/backend files over broad edits to shared engine code.
5. Do not define the Xbox as ordinary `WIN32`; use `DP_PLATFORM_XBOX`.
6. Do not introduce proprietary XDK headers, libraries, tools, samples, BIOS files, keys, EEPROM data, dashboards, or retail game data.
7. Never assume a graphics feature exists. Record the NV2A implementation or deliberate fallback in `wiki/Feature-Support-Matrix.md`.
8. Standard 64 MB memory is the acceptance target. Treat 128 MB as diagnostic-only.
9. Keep patches small enough to identify the gate they unlock.
10. Attach reproducible evidence to every PR.
11. Canonical port documentation lives in `wiki/`. Where initial issue text names `docs/xbox-port/...`, update or add the corresponding wiki page instead of creating a second documentation tree.
12. Do not create a second issue roadmap. Extend or split the live issues under epic #1 and keep `wiki/Issue-Map.md` synchronized.

## Preferred implementation order

Scope/reference/audit/renderer spike -> nxdk smoke XBE -> core compile -> boot console -> filesystem/timing/logging -> 64 MB enforcement -> clear/present -> textured mesh -> 2D -> BSP/lightmaps -> models/materials/effects -> deterministic route -> telemetry -> xemu regression -> hardware soak.

## Stop conditions

Do not stack later renderer or content work on an unstable earlier gate. If a patch cannot explain its inputs, outputs, fallback behavior, memory ownership, and validation method, split it before implementation.
