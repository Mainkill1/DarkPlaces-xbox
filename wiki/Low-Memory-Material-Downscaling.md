# Low-Memory Material Downscaling

The canonical `xbox/release` build generates a stock-memory texture override
from the immutable Nexuiz 2.5.2 archive. The source archive and its PK3 files
remain byte-for-byte unchanged. The generated pack is a private engineering
artifact and is not committed or independently redistributed.

## Scope and policy

- The stock target is the 64 MiB Xbox. The same conservative content is used
  when the XBE detects 128 MiB; 128 MiB remains diagnostic-only.
- Every effective TGA whose width or height exceeds 256 pixels is reduced by
  repeated two-to-one box filtering until both dimensions are at most 256.
- External Q3 lightmaps matching `maps/<map>/lm_NNNN.tga` use a separate
  64x64 ceiling. The Xbox classic build materializes a bounded loader which
  validates the set and then decodes, converts, uploads, and frees one lightmap
  at a time. This bounds the transient decoded image and the non-picmipped
  resident lightmaps.
- True-color 24-bit and 32-bit TGA images and 8-bit grayscale TGA images are
  supported, including their RLE forms used by the pinned content. The corpus's
  raw and RLE 8-bit indexed TGAs with 24-bit palettes are also decoded. Invalid
  palette indices and unsupported oversized input are staging errors, never
  silently copied.
- Alpha-bearing images use premultiplied-alpha averaging while filtering, then
  return to straight alpha. This avoids dark fringes at transparent edges.
- Generated images use uncompressed TGA entries in a stored PK3. That bounds
  each general runtime source decode to at most 256 KiB, each external-lightmap
  decode to 16 KiB, and avoids a second DEFLATE workspace at the loading
  boundary.
- Pack entries are sorted, use fixed ZIP metadata, and include a manifest with
  source/output dimensions and SHA-256 hashes. Identical verified inputs must
  produce an identical override pack.

## Ownership and precedence

`tools/xbox/build_lowmem_texture_pack.py` owns conversion and deterministic PK3
creation. `tools/xbox/stage_classic_release.py` invokes it only after staging
the complete verified data tree and records the derived pack identity in
`CONTENT-IDENTITY.json`.

`tools/xbox/patch_classic_lightmaps.py` owns the Xbox-only external-lightmap
streaming change. It accepts only the locked classic `model_brush.c` identity;
the desktop source and internal BSP lightmap path remain unchanged.

The output is `data/zzzz-xbox-lowmem.pk3`. The pinned engine sorts PK3 names in
ascending order and prepends each pack to the search path, so this final name
overrides the same virtual paths from the original packs. Loose files retain
the engine's existing higher priority.

## Validation boundary

Host tests cover TGA decoding, RLE handling, alpha-aware filtering, malformed
input rejection, deterministic PK3 bytes, effective cross-pack precedence, and
content-identity reconciliation. The complete pinned corpus produces 1,952
converted assets in a 246,640,469-byte derived pack under the 256/64 policy.
The canonical release must still compile,
link, produce an XBE, produce and verify an XISO, then pass a new stock-64-MiB
runtime trace. Downscaling alone is not a claim that a map loads or gameplay is
complete.
