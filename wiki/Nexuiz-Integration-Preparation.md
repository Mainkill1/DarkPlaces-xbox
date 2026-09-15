# Nexuiz integration preparation

## Scope and branch isolation

Branch: `port/nexuiz-integration-prep`, based on foundation commit
`bbdf722e6c7cdb25627e738ed903fa97fdceb9dc`.

This is preparatory work for the **Nexuiz Classic 2.5.2-derived offline stress
world**, not the commercial remake, complete multiplayer Nexuiz, or a runnable
Xbox game. The original foundation branch, its nxdk pin, `xbox/Makefile`,
`xbox/config_xbox.h`, and smoke source are unchanged.

This slice supports [#4](https://github.com/Mainkill1/DarkPlaces-xbox/issues/4),
[#6](https://github.com/Mainkill1/DarkPlaces-xbox/issues/6),
[#15](https://github.com/Mainkill1/DarkPlaces-xbox/issues/15), and
[#26](https://github.com/Mainkill1/DarkPlaces-xbox/issues/26). It closes none of them.
The [existing epic](https://github.com/Mainkill1/DarkPlaces-xbox/issues/1) remains
the execution roadmap.

## Implemented now

`tools/xbox/nexuiz_prepare.py` inventories local PK3s and builds a deterministic,
explicitly selected **unconverted** package. It records source and asset SHA-256,
source origins, per-file license/attribution declarations, included notices, and
byte counts. Cross-pack overrides are reported; the selection must name the
source pack for every asset rather than guessing load order.

The tool does not execute scripts, download game data, extract archive paths to
the host filesystem, determine an asset's license, infer its dependencies, or
convert it for NV2A. `xbox_ready` is always false. The release name is an intended
baseline, not authentication of arbitrary local files as an official release.

`thread_null.c` now decrements reference counts correctly and includes only the
thread API instead of the engine-wide `quakedef.h`. Host tests compile and run the
actual source. A separate CI job cross-compiles that same source through the
pinned nxdk wrapper and checks the resulting i386 COFF header. Neither test is an
engine link or Xbox execution result. No threads or pretend synchronization have
been added; this backend is only appropriate when callers really are single-threaded.

## Prepare source content

Use the **Classic** release linked by [Alientrap](https://www.alientrap.com/games/nexuiz/)
and its [2.5.2 release directory](https://sourceforge.net/projects/nexuiz/files/NexuizRelease/Nexuiz%202.5.2/).
Preserve the original download and record its checksum separately. Extract the
outer distribution into a local working area; point the inventory command at the
folder directly containing its `.pk3` files. Keep bulk data outside this repository.
No upstream archive checksum or real game-content selection is claimed by this branch.

Python 3.10 or newer is sufficient; no pip packages are required.

```sh
python3 tools/xbox/nexuiz_prepare.py inventory \
  --data-dir /work/Nexuiz/data \
  --output /work/nexuiz-inventory.json
```

The report hashes each pack and every contained file, checks source stability, and
lists paths present in more than one pack. The default host-processing ceilings
are 64 MiB per asset and 2047 MiB total uncompressed content. Override them with
`--max-asset-bytes` and `--max-total-bytes` when deliberately inspecting larger
sources. These are host processing limits, **not** the Xbox's runtime memory budget.

Virtual asset paths must be ASCII, relative, traversal-free, and shorter than 128
bytes, matching the current engine `MAX_QPATH` capacity. Duplicate/case-colliding
names, encrypted archives, archive symlinks, and compression other than stored or
deflated ZIP entries are rejected. This conservative policy may require source
cleanup or an explicit future policy change. It is not a FATX filename validator:
internal PK3 paths are not individual FATX files. The generated outer names are
short: `data/xboxprep.pk3` and `manifest.json`.

## Select and stage a small audited subset

Create a JSON selection using the inventory's exact names and hashes. Start with
the bootstrap files, one chosen map, its proven dependencies, and its notices;
do not copy every desktop asset or invent dummy QuakeC programs to force a boot.
The example below describes the schema, not verified Nexuiz asset names or hashes.
Replace the uppercase example values; invalid hashes are rejected.

```json
{
  "schema_version": 1,
  "release": "nexuiz-classic-2.5.2",
  "profile": "first-map-preparation",
  "max_asset_bytes": 8388608,
  "max_total_bytes": 33554432,
  "sources": [
    {"file": "SOURCE.pk3", "sha256": "PACK_SHA256_FROM_INVENTORY", "origin": "VERIFIED_UPSTREAM_LOCATION"}
  ],
  "assets": [
    {
      "path": "maps/CHOSEN_MAP.bsp",
      "source": "SOURCE.pk3",
      "sha256": "ASSET_SHA256_FROM_INVENTORY",
      "license": "REVIEWED_LICENSE_IDENTIFIER",
      "attribution": "RECORDED_AUTHOR_AND_SOURCE",
      "notice": "licenses/content.txt"
    }
  ],
  "notices": [
    {
      "file": "NOTICE.txt",
      "path": "licenses/content.txt",
      "sha256": "NOTICE_FILE_SHA256",
      "origin": "ORIGINAL_NOTICE_LOCATION"
    }
  ]
}
```

Every selected file needs a declared license, attribution, and a notice path.
The notice must either be another selected PK3 file or an entry in `notices`.
External notices are useful when the distribution keeps COPYING/license files
outside its packs. Their file paths are relative to `--notice-dir`, defaulting to
the selection file's directory. Notice contents are copied unchanged and hashed;
symlinks and traversal are rejected. Declarations do not replace the review in #6.

```sh
python3 tools/xbox/nexuiz_prepare.py stage \
  --data-dir /work/Nexuiz/data \
  --selection /work/nexuiz-selection.json \
  --notice-dir /work/Nexuiz \
  --output /work/nexuiz-prepared-001
```

The output directory must not exist and must be outside the source data folder.
Use a different output for another run; existing outputs are never intentionally
replaced. Do not concurrently write the same output path or modify source files.
A failed build cleans its temporary staging directory. Nothing is silently dropped.

The package stores selected bytes without ZIP compression, uses fixed timestamps,
sorted names, and fixed file attributes, and verifies output CRCs. For identical
inputs and tool bytes, reordering selection entries leaves the pack and manifest
unchanged. Stored ZIP avoids requiring an inflater for these entries in a future
runtime; it does not implement that runtime's PK3 reader or make texture data GPU-ready.
The separate manifest includes the normalized selection hash and tool source hash.
Do not mix evidence/checksums back into the input directory for an XISO build.

Package byte totals are **not** resident memory estimates. BSP expansion, decoded
images, geometry, lightmaps, animations, engine state, stacks, and loading peaks
still need measurement and conversion work. The manifest marks dependency closure,
material compatibility, and runtime memory as unchecked/unmeasured.

## Validate this slice

```sh
python3 -m unittest discover -s tests -p 'test_xbox_nexuiz_content.py' -v
python3 -m unittest discover -s tests -p 'test_xbox_thread_null.py' -v
```

The C test requires a host compiler (`cc`, or `CC`). All asset tests generate their
own small fixtures; they do not redistribute a real Nexuiz map or license it by
assumption. Existing full-repository host tests, the foundation XBE build, and the
desktop SDL build remain separate regression checks. See
`evidence/nexuiz-prep/local-validation.json` for the local test boundary and evidence.

## Next engine integration boundary

After the smoke result, use #8/#9/#10/#12 for an **engine-linked** target that calls
normal `Sys_Main`/`Host_Init`, mounts verified bootstrap content, logs failures, and
executes a bounded frame loop. Do not relabel this package tool or the existing
smoke as that milestone. Keep a distinct build/output directory and profile.

Before using the null-thread backend in that link, #15 must remove or bound the
large desktop worker table in `taskqueue.c` and audit callbacks/worker assumptions.
Before a real map is runnable, #13/#14 must measure allocations and #16–#22 must
provide the required native renderer and material/resource conversions. The
continuous world and deterministic route remain #25/#27, not an implicit promise
made by successfully packing `.bsp`, `.dat`, textures, or scripts.
