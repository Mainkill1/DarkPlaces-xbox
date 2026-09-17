/* SPDX-License-Identifier: GPL-2.0-or-later
 * Private types and hard limits for the direct Original Xbox NV2A renderer.
 */
#ifndef R_XBOX_INTERNAL_H
#define R_XBOX_INTERNAL_H

#include <stddef.h>
#include <stdint.h>

#include "qtypes.h"

#define R_XBOX_TEXTURE_UNITS 4u
#define R_XBOX_FRAMES_IN_FLIGHT 3u

#define R_XBOX_DYNAMIC_VERTEX_BYTES (1536u * 1024u)
#define R_XBOX_DYNAMIC_INDEX_BYTES (512u * 1024u)
#define R_XBOX_CONSTANT_BYTES (256u * 1024u)

#define R_XBOX_TEXTURE_RESIDENT_LIMIT (20u * 1024u * 1024u)
#define R_XBOX_TEXTURE_SCRATCH_LIMIT (2u * 1024u * 1024u)
#define R_XBOX_METADATA_LIMIT (2u * 1024u * 1024u)

typedef enum r_xbox_init_stage_e
{
    R_XBOX_INIT_NONE = 0,
    R_XBOX_INIT_VIDEO,
    R_XBOX_INIT_BACKEND,
    R_XBOX_INIT_TARGETS,
    R_XBOX_INIT_RINGS,
    R_XBOX_INIT_TEXTURES,
    R_XBOX_INIT_PROGRAMS,
    R_XBOX_INIT_MATERIALS,
    R_XBOX_INIT_DRAW2D,
    R_XBOX_INIT_WORLD,
    R_XBOX_INIT_MODELS,
    R_XBOX_INIT_READY
} r_xbox_init_stage_t;

typedef enum r_xbox_fallback_reason_e
{
    R_XBOX_FALLBACK_UNSUPPORTED_BLEND = 1u << 0,
    R_XBOX_FALLBACK_UNSUPPORTED_MATERIAL = 1u << 1,
    R_XBOX_FALLBACK_UNSUPPORTED_TEXTURE = 1u << 2,
    R_XBOX_FALLBACK_TEXTURE_BUDGET = 1u << 3,
    R_XBOX_FALLBACK_INDEX_RANGE = 1u << 4,
    R_XBOX_FALLBACK_INVALID_DRAW = 1u << 5,
    R_XBOX_FALLBACK_DISABLED_EFFECT = 1u << 6,
    R_XBOX_FALLBACK_MISSING_CONTENT = 1u << 7
} r_xbox_fallback_reason_t;

typedef struct r_xbox_init_state_s
{
    r_xbox_init_stage_t completed_stage;
    qbool video_mode_set;
    qbool pbkit_initialized;
    qbool backend_initialized;
    qbool textures_initialized;
    qbool programs_initialized;
    qbool draw2d_initialized;
} r_xbox_init_state_t;

#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
_Static_assert(R_XBOX_TEXTURE_UNITS == 4u, "NV2A exposes four texture stages");
_Static_assert((R_XBOX_DYNAMIC_VERTEX_BYTES & 15u) == 0u,
               "dynamic vertex ring must be 16-byte aligned");
_Static_assert((R_XBOX_DYNAMIC_INDEX_BYTES & 15u) == 0u,
               "dynamic index ring must be 16-byte aligned");
#endif

#endif
