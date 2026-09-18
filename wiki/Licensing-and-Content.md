# Licensing and Content

## Engine/toolchain

DarkPlaces is GPL-licensed; preserve notices and source obligations. nxdk and pbGL
are open-source components with their own notices. Ogg/Vorbis notices also travel
with the corresponding source/release materials. Record exact source commits in
`xbox/release/release-inputs.json` and in every produced `BUILD-IDENTITY.txt`.

## Prohibited repository content

Do not commit:

- proprietary Microsoft XDK files or derived headers/libraries;
- Xbox BIOS or kernel images;
- EEPROM data, HDD keys, certificates, or console secrets;
- retail game executables/data;
- unverified ripped assets;
- firmware or copyrighted files not licensed for redistribution.

## Nexuiz 2.5.2 source package

The canonical build consumes the historical `nexuiz-252.zip` release as an
**external input**. It is not stored in normal Git history and is no longer sourced
from expiring GitHub Actions artifacts.

The immutable build identity is:

```text
filename: nexuiz-252.zip
bytes:    931253731
SHA256:   a5e27ebcc9775c4a490d0d3536c32e4a8f8f96b038c0b6a78d1823c37a962000
MD5:      d750bc328e58df8492f8d88bdcf818cb
```

The SHA-256 is the build-security identity; MD5 is retained only to cross-reference
the historical release. The release wrapper can download the archive from the
historical Nexuiz 2.5.2 SourceForge project location or accept a caller-supplied
archive path. It verifies the complete file before opening or staging it.

Fetching an original release for a local developer build is separate from a legal
decision to redistribute that data inside our own downloadable Xbox image. Do not
interpret a reproducible local acquisition path as blanket permission to mirror or
republish every file in the package.

## Content staging

`tools/xbox/stage_classic_release.py` stages the complete release `data/` subtree
for engineering builds so missing maps/gamecode/assets are not silently hidden by
a benchmark-only subset. Before writing files it rejects traversal, absolute paths,
case/duplicate collisions, symlinks, encryption, unsupported ZIP methods and
unbounded file/total sizes.

The generated `CONTENT-IDENTITY.json` records:

- verified outer archive SHA-256;
- detected source `data/` prefix;
- source and final staged file counts;
- total staged bytes;
- path, byte size and SHA-256 for every staged file.

For the stock-memory candidate, staging additionally creates
`zzzz-xbox-lowmem.pk3` from effective TGA assets larger than 512 pixels on
either axis. The derived pack is deterministic and records source/output hashes
and dimensions in its embedded manifest; `CONTENT-IDENTITY.json` records the
final pack hash. The source PK3s are not edited. This local engineering
derivative is subject to the same source attribution and redistribution audit
as its inputs and must not be committed as a substitute for the external
archive.

Xbox startup defaults are generated separately as `xbox-defaults.cfg`. If the
original package contains `autoexec.cfg`, its existing contents are preserved and
an `exec xbox-defaults.cfg` line is appended rather than replacing game startup
configuration.

## Full release audit still required

Do not assume every file in a historical game package has one uniform license.
Before publishing an engine-plus-content image, issue #26 must produce a
file/category-level manifest covering maps, textures, models, sounds, scripts,
fonts, gamecode and derivative conversions required by the full playable game and
benchmark. Pin the complete map/mode/campaign inventory; license exceptions or
content omissions must remain visible and owner-approved.

Prepared or converted Xbox assets retain their source obligations. Store source
attribution and deterministic conversion command/tool/output hashes next to the
pack manifest.

## Release shapes

A release may be:

1. Engine-only XBE/XISO tooling requiring the user to provide the verified original data.
2. Engine plus fully audited redistributable game content and the benchmark pack.
3. Developer artifact containing original content for private validation under the applicable source terms.
4. Developer artifact with generated test geometry only.

Do not publish option 2 until the licensing audit is complete. A local engineering
ISO, developer fixture or demo-only data pack is not automatically a redistributable
complete-game release.
