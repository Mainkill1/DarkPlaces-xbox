# Licensing and Content

## Engine/toolchain

DarkPlaces is GPL-licensed; preserve notices and source obligations. nxdk is open source but contains components under several compatible licenses. Record the exact nxdk revision in release materials.

## Prohibited repository content

Do not commit:

- proprietary Microsoft XDK files or derived headers/libraries;
- Xbox BIOS or kernel images;
- EEPROM data, HDD keys, certificates, or console secrets;
- retail game executables/data;
- unverified ripped assets;
- firmware or copyrighted files not licensed for redistribution.

## Nexuiz data

Do not assume every file in a historical game package has one uniform license. The content audit must produce a file/category-level manifest for the map, textures, models, sounds, scripts, fonts, and derivative conversions required by the full playable game and the benchmark. Pin the complete map/mode/campaign inventory; license exceptions or content omissions must be visible and approved.

Prepared Xbox assets retain the license obligations of their sources. Store source attribution and conversion command/hash next to the pack manifest.

## Release shapes

A release may be:

1. Engine-only XBE/XISO tooling requiring the user to provide data.
2. Engine plus fully audited redistributable game content and the benchmark pack.
3. Developer artifact with generated test geometry only.

Do not publish option 2 until the licensing issue is complete. A developer fixture or demo-only data pack is not the complete playable-game release.
