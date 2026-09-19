#!/usr/bin/env python3
"""Materialize bounded Xbox model-loading adaptations in model_brush.c."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile


EXPECTED_SHA256 = "e79ca0cf9b8f6abe179b0aef6d06ab94cfaf4a1107c61c16a14ea6a064d508bc"

DECLARATIONS_OLD = '''\
\tunsigned char *convertedpixels;
\tchar mapname[MAX_QPATH];
'''

DECLARATIONS_NEW = '''\
\tunsigned char *convertedpixels;
\tunsigned char *externalpixels = NULL;
\tchar mapname[MAX_QPATH];
'''

EXTERNAL_OLD = '''\
\t\tFS_StripExtension(loadmodel->name, mapname, sizeof(mapname));
\t\tinpixels[0] = loadimagepixelsbgra(va("%s/lm_%04d", mapname, 0), false, false);
\t\tif(!inpixels[0])
\t\t\treturn;

\t\t// using EXTERNAL lightmaps instead
\t\tif(image_width != (int) CeilPowerOf2(image_width) || image_width != image_height)
\t\t{
\t\t\tMem_Free(inpixels[0]);
\t\t\tHost_Error("Mod_Q3BSP_LoadLightmaps: invalid external lightmap size in %s",loadmodel->name);
\t\t}

\t\tsize = image_width;
\t\tbytesperpixel = 4;
\t\trgbmap[0] = 0;
\t\trgbmap[1] = 1;
\t\trgbmap[2] = 2;
\t\texternal = true;

\t\tfor(count = 1; ; ++count)
\t\t{
\t\t\tinpixels[count] = loadimagepixelsbgra(va("%s/lm_%04d", mapname, count), false, false);
\t\t\tif(!inpixels[count])
\t\t\t\tbreak; // we got all of them
\t\t\tif(image_width != size || image_height != size)
\t\t\t{
\t\t\t\tfor(i = 0; i <= count; ++i)
\t\t\t\t\tMem_Free(inpixels[i]);
\t\t\t\tHost_Error("Mod_Q3BSP_LoadLightmaps: invalid external lightmap size in %s",loadmodel->name);
\t\t\t}
\t\t}
'''

EXTERNAL_NEW = '''\
\t\tFS_StripExtension(loadmodel->name, mapname, sizeof(mapname));
\t\texternalpixels = loadimagepixelsbgra(va("%s/lm_%04d", mapname, 0), false, false);
\t\tif(!externalpixels)
\t\t\treturn;

\t\t// using EXTERNAL lightmaps instead
\t\tif(image_width != (int) CeilPowerOf2(image_width) || image_width != image_height)
\t\t{
\t\t\tMem_Free(externalpixels);
\t\t\tHost_Error("Mod_Q3BSP_LoadLightmaps: invalid external lightmap size in %s",loadmodel->name);
\t\t}

\t\tsize = image_width;
\t\tbytesperpixel = 4;
\t\trgbmap[0] = 0;
\t\trgbmap[1] = 1;
\t\trgbmap[2] = 2;
\t\texternal = true;

\t\t// Xbox: count and validate external lightmaps one at a time.
\t\tMem_Free(externalpixels);
\t\texternalpixels = NULL;
\t\tfor(count = 1; count < 10000; ++count)
\t\t{
\t\t\texternalpixels = loadimagepixelsbgra(va("%s/lm_%04d", mapname, count), false, false);
\t\t\tif(!externalpixels)
\t\t\t\tbreak; // we got all of them
\t\t\tif(image_width != size || image_height != size)
\t\t\t{
\t\t\t\tMem_Free(externalpixels);
\t\t\t\tHost_Error("Mod_Q3BSP_LoadLightmaps: invalid external lightmap size in %s",loadmodel->name);
\t\t\t}
\t\t\tMem_Free(externalpixels);
\t\t\texternalpixels = NULL;
\t\t}
\t\tif(count == 10000)
\t\t\tHost_Error("Mod_Q3BSP_LoadLightmaps: too many external lightmaps in %s",loadmodel->name);
\t\tif (developer_loading.integer)
\t\t\tCon_Printf("Xbox external lightmaps counted: %i at %ix%i\\n", count, size, size);
'''

BLANK_CHECK_OLD = '''\
\tif (endlightmap == 1 && count > 1)
\t{
\t\tc = inpixels[1];
\t\tfor (i = 0;i < size*size;i++)
\t\t{
\t\t\tif (c[bytesperpixel*i + rgbmap[0]])
\t\t\t\tbreak;
\t\t\tif (c[bytesperpixel*i + rgbmap[1]])
\t\t\t\tbreak;
\t\t\tif (c[bytesperpixel*i + rgbmap[2]])
\t\t\t\tbreak;
\t\t}
\t\tif (i == size*size)
\t\t{
\t\t\t// all pixels in the unused lightmap were black...
\t\t\tloadmodel->brushq3.deluxemapping = false;
\t\t}
\t}
'''

BLANK_CHECK_NEW = '''\
\tif (endlightmap == 1 && count > 1)
\t{
\t\tif (external)
\t\t{
\t\t\texternalpixels = loadimagepixelsbgra(va("%s/lm_%04d", mapname, 1), false, false);
\t\t\tif (!externalpixels)
\t\t\t\tHost_Error("Mod_Q3BSP_LoadLightmaps: external lightmap disappeared in %s",loadmodel->name);
\t\t\tc = externalpixels;
\t\t}
\t\telse
\t\t\tc = inpixels[1];
\t\tfor (i = 0;i < size*size;i++)
\t\t{
\t\t\tif (c[bytesperpixel*i + rgbmap[0]])
\t\t\t\tbreak;
\t\t\tif (c[bytesperpixel*i + rgbmap[1]])
\t\t\t\tbreak;
\t\t\tif (c[bytesperpixel*i + rgbmap[2]])
\t\t\t\tbreak;
\t\t}
\t\tif (i == size*size)
\t\t{
\t\t\t// all pixels in the unused lightmap were black...
\t\t\tloadmodel->brushq3.deluxemapping = false;
\t\t}
\t\tif (external)
\t\t{
\t\t\tMem_Free(externalpixels);
\t\t\texternalpixels = NULL;
\t\t}
\t}
'''

UPLOAD_BEGIN_OLD = '''\
\tfor (i = 0;i < count;i++)
\t{
\t\t// figure out which merged lightmap texture this fits into
\t\tint lightmapindex = i >> (loadmodel->brushq3.deluxemapping + power2);
\t\tfor (k = 0;k < size*size;k++)
\t\t{
\t\t\tconvertedpixels[k*4+0] = inpixels[i][k*bytesperpixel+rgbmap[0]];
\t\t\tconvertedpixels[k*4+1] = inpixels[i][k*bytesperpixel+rgbmap[1]];
\t\t\tconvertedpixels[k*4+2] = inpixels[i][k*bytesperpixel+rgbmap[2]];
\t\t\tconvertedpixels[k*4+3] = 255;
\t\t}
'''

UPLOAD_BEGIN_NEW = '''\
\tfor (i = 0;i < count;i++)
\t{
\t\t// Xbox: decode each external lightmap only for its upload.
\t\tif (external)
\t\t{
\t\t\texternalpixels = loadimagepixelsbgra(va("%s/lm_%04d", mapname, i), false, false);
\t\t\tif (!externalpixels || image_width != size || image_height != size)
\t\t\t\tHost_Error("Mod_Q3BSP_LoadLightmaps: external lightmap changed in %s",loadmodel->name);
\t\t\tc = externalpixels;
\t\t}
\t\telse
\t\t\tc = inpixels[i];
\t\t// figure out which merged lightmap texture this fits into
\t\tint lightmapindex = i >> (loadmodel->brushq3.deluxemapping + power2);
\t\tfor (k = 0;k < size*size;k++)
\t\t{
\t\t\tconvertedpixels[k*4+0] = c[k*bytesperpixel+rgbmap[0]];
\t\t\tconvertedpixels[k*4+1] = c[k*bytesperpixel+rgbmap[1]];
\t\t\tconvertedpixels[k*4+2] = c[k*bytesperpixel+rgbmap[2]];
\t\t\tconvertedpixels[k*4+3] = 255;
\t\t}
'''

UPLOAD_END_OLD = '''\
\t\t\telse
\t\t\t\tloadmodel->brushq3.data_lightmaps [lightmapindex] = R_LoadTexture2D(loadmodel->texturepool, va("lightmap%04i", lightmapindex), size, size, convertedpixels, TEXTYPE_BGRA, TEXF_FORCELINEAR | TEXF_PRECACHE | (gl_texturecompression_q3bsplightmaps.integer ? TEXF_COMPRESS : 0), NULL);
\t\t}
\t}

\tMem_Free(convertedpixels);
\tif(external)
\t{
\t\tfor(i = 0; i < count; ++i)
\t\t\tMem_Free(inpixels[i]);
\t}
'''

UPLOAD_END_NEW = '''\
\t\t\telse
\t\t\t\tloadmodel->brushq3.data_lightmaps [lightmapindex] = R_LoadTexture2D(loadmodel->texturepool, va("lightmap%04i", lightmapindex), size, size, convertedpixels, TEXTYPE_BGRA, TEXF_FORCELINEAR | TEXF_PRECACHE | (gl_texturecompression_q3bsplightmaps.integer ? TEXF_COMPRESS : 0), NULL);
\t\t}
\t\tif (external)
\t\t{
\t\t\tMem_Free(externalpixels);
\t\t\texternalpixels = NULL;
\t\t}
\t}
\tif (external && developer_loading.integer)
\t\tCon_Printf("Xbox external lightmap streaming complete\\n");

\tMem_Free(convertedpixels);
'''

PATCH_DECLARATIONS_OLD = '''\
\tpatchtess_t *patchtess = NULL;
\tint patchtesscount = 0;
\tqboolean again;
'''

PATCH_DECLARATIONS_NEW = '''\
\tpatchtess_t *patchtess = NULL;
\tint patchtesscount = 0;
\tint patchtesscapacity = 0;
\tqboolean again;
'''

PATCH_ALLOCATION_OLD = '''\
\tif(count > 0)
\t\tpatchtess = (patchtess_t*) Mem_Alloc(tempmempool, count * sizeof(*patchtess));
'''

PATCH_ALLOCATION_NEW = '''\
\t// Xbox: temporary tessellation state is needed only for patch faces.
\tfor (i = 0; i < count; ++i)
\t\tif (LittleLong(in[i].type) == Q3FACETYPE_PATCH)
\t\t\t++patchtesscapacity;
\tif (patchtesscapacity > 0)
\t\tpatchtess = (patchtess_t*) Mem_Alloc(tempmempool, patchtesscapacity * sizeof(*patchtess));
\tif (developer_loading.integer)
\t\tCon_Printf("Xbox patch tessellation scratch: %i of %i faces, %i bytes\\n", patchtesscapacity, count, patchtesscapacity * (int)sizeof(*patchtess));
'''

PATCH_STORE_OLD = '''\
\t\t\t// store it for the LOD grouping step
\t \t\tpatchtess[patchtesscount].info.xsize = patchsize[0];
'''

PATCH_STORE_NEW = '''\
\t\t\t// store it for the LOD grouping step
\t\t\tif (patchtesscount >= patchtesscapacity)
\t\t\t\tHost_Error("Mod_Q3BSP_LoadFaces: patch tessellation capacity exceeded in %s", loadmodel->name);
\t \t\tpatchtess[patchtesscount].info.xsize = patchsize[0];
'''

Q3_PORTALS_OLD = '''\
	// the MakePortals code works fine on the q3bsp data as well
	Mod_Q1BSP_MakePortals();
'''

Q3_PORTALS_NEW = '''\
	// Xbox: Q3 BSP files already provide PVS data and node/leaf bounds.  Runtime
	// portal reconstruction is an optional culling accelerator, but its recursive
	// split representation exhausts the stock-memory loading headroom.
	loadmodel->brush.data_portals = NULL;
	loadmodel->brush.num_portals = 0;
	loadmodel->brush.data_portalpoints = NULL;
	loadmodel->brush.num_portalpoints = 0;
	if (developer_loading.integer)
		Con_Printf("Xbox Q3 portals disabled; using BSP PVS/frustum fallback\\n");
'''


def materialize(source: Path, output: Path) -> None:
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"unexpected pinned model_brush.c identity: {digest}")
    text = data.decode("utf-8")
    replacements = (
        (DECLARATIONS_OLD, DECLARATIONS_NEW, "declarations"),
        (EXTERNAL_OLD, EXTERNAL_NEW, "external scan"),
        (BLANK_CHECK_OLD, BLANK_CHECK_NEW, "blank-lightmap check"),
        (UPLOAD_BEGIN_OLD, UPLOAD_BEGIN_NEW, "upload start"),
        (UPLOAD_END_OLD, UPLOAD_END_NEW, "upload cleanup"),
        (PATCH_DECLARATIONS_OLD, PATCH_DECLARATIONS_NEW, "patch declarations"),
        (PATCH_ALLOCATION_OLD, PATCH_ALLOCATION_NEW, "patch allocation"),
        (PATCH_STORE_OLD, PATCH_STORE_NEW, "patch capacity check"),
        (Q3_PORTALS_OLD, Q3_PORTALS_NEW, "Q3 portal fallback"),
    )
    for old, new, label in replacements:
        if text.count(old) != 1:
            raise SystemExit(f"pinned model_brush.c {label} did not match exactly once")
        text = text.replace(old, new)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=output.name + ".", dir=output.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as temporary:
            temporary.write(text)
        os.replace(temporary_name, output)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"usage: {argv[0]} SOURCE OUTPUT", file=sys.stderr)
        return 2
    materialize(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
