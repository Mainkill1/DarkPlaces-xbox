# Agent Rules for the Original Xbox Port

Read `PORTING.md`, `wiki/Home.md`, and the [master port epic](https://github.com/Mainkill1/DarkPlaces-xbox/issues/1) before changing code.

## Hard rules

1. The owner approved Option B: fully playable Nexuiz Classic offline plus LAN host/join, retaining autoplay and the continuous stress world. Read `wiki/Playable-Game-and-LAN.md`; benchmark-only completion is superseded. Stock 64 MiB memory is required, with a homebrew-capable launch environment.
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
12. Do not create a second issue roadmap. Extend the live issues under epic #1; #35 owns offline gameplay and #36 owns LAN. Keep `wiki/Issue-Map.md` synchronized.
13. Preserve the actual client/server and required gamecode in the playable link. Audio, persistence and LAN are release requirements; null/disabled subsystems are diagnostic gates only.
14. Default automatic quality OFF, preserve controller graphics choices, and do not let autoplay restart during a live game or a failed LAN join.

## Preferred implementation order

Approved playable/LAN scope -> actual core/system/filesystem link -> normal Host_Init -> 64 MiB enforcement -> native mesh/2D/BSP/material/model renderer -> complete offline matches with audio and persistence -> LAN host/join -> full content coverage and benchmark modes -> xemu/hardware acceptance. Network transport work can proceed alongside native core/renderer work. The existing smoke stays diagnostic; another standalone screen is not the next game milestone.

## Stop conditions

Do not stack later renderer or content work on an unstable earlier gate. If a patch cannot explain its inputs, outputs, fallback behavior, memory ownership, and validation method, split it before implementation.
