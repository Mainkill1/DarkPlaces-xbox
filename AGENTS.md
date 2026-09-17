# Agent Rules for the Original Xbox Port

Read `PORTING.md`, `wiki/Home.md`, and the [master port epic](https://github.com/Mainkill1/DarkPlaces-xbox/issues/1) before changing code.

## Hard rules

1. The owner approved Option B: fully playable Nexuiz Classic offline plus LAN host/join, retaining autoplay and the continuous stress world. Read `wiki/Playable-Game-and-LAN.md`; benchmark-only completion is superseded. Stock 64 MiB memory is required, with a homebrew-capable launch environment.
2. Do not claim “Xbox support” from a compile-only result. State the exact gate reached: compiled, linked, XBE produced, booted, frame presented, map loaded, complete route finished, or soak passed.
3. Preserve the desktop `make sdl-release` build.
4. Prefer Xbox-specific files over broad edits to shared engine code.
5. Do not define the Xbox as ordinary `WIN32`; use `DP_PLATFORM_XBOX`.
6. Do not introduce proprietary XDK headers, libraries, tools, samples, BIOS files, keys, EEPROM data, dashboards, or unapproved content.
7. Never assume a graphics feature exists. Record the NV2A implementation or deliberate fallback in `wiki/Feature-Support-Matrix.md`.
8. Standard 64 MB memory is the acceptance target. Treat 128 MB as diagnostic-only.
9. Keep patches small enough to identify the gate they unlock.
10. Attach reproducible evidence to every PR.
11. Canonical port documentation lives in `wiki/`. Where initial issue text names `docs/xbox-port/...`, update or add the corresponding wiki page instead of creating a second documentation tree.
12. Do not create a second issue roadmap. Extend the live issues under epic #1; #35 owns offline gameplay and #36 owns LAN. Keep `wiki/Issue-Map.md` synchronized.
13. Preserve the actual client/server and required gamecode in the playable link. Audio, persistence and LAN are release requirements; null/disabled subsystems are diagnostic gates only.
14. Default automatic quality OFF, preserve controller graphics choices, and do not let autoplay restart during a live game or a failed LAN join.
15. **Do not create another Xbox game build route.** `xbox/release` is the canonical first end-to-end build entry, wrapping the integrated `xbox/classic` candidate. `xbox/game` remains the modern direct-`RENDERPATH_XBOX` backend-development path. Foundation/input targets remain diagnostics.
16. External inputs are immutable. Use `xbox/release/release-inputs.json`; never replace exact commits or the Nexuiz SHA-256 with moving branches, tags, mirrors without hashes, or expiring Actions artifacts.
17. The complete Nexuiz archive is an external build input. Do not commit it. Engineering staging uses the full verified `data/` tree; public redistribution still requires the licensing/content audit.

## Build ownership

```text
xbox/Makefile       foundation diagnostic
xbox/inputcheck/    controller diagnostic
xbox/game/          modern direct-native renderer development
xbox/classic/       integrated Nexuiz-era engine/platform implementation
xbox/release/       canonical dependency/staging/build/package entry
```

A clean integration attempt begins with:

```sh
make -C xbox/release bootstrap
make -C xbox/release all
```

`bootstrap` is the explicit network/acquisition step. `preflight`, `stage`, `engine` and `package` are expected to work without hidden downloads. Fix failures against the locked source/content identity rather than adding a parallel target.

## Preferred implementation order

Approved playable/LAN scope -> reproducible release inputs -> actual integrated engine build -> normal host/filesystem initialization -> 64 MiB enforcement -> NV2A/pbGL rendering coverage and direct-native migration where required -> complete offline matches with bounded stereo audio and persistence -> LAN host/join -> full content coverage and benchmark modes -> xemu/hardware acceptance. Network transport work can proceed alongside renderer work. The existing smoke stays diagnostic; another standalone screen is not a game milestone.

## Stop conditions

Do not stack later renderer or content work on an unstable earlier gate. If a patch cannot explain its inputs, outputs, fallback behavior, memory ownership, and validation method, split it before implementation.
