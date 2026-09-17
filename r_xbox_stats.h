/* SPDX-License-Identifier: GPL-2.0-or-later
 * Stable counters and one-shot diagnostics for the direct NV2A renderer.
 */
#ifndef R_XBOX_STATS_H
#define R_XBOX_STATS_H

#include <stddef.h>
#include <stdint.h>

typedef struct r_xbox_stats_s
{
    uint32_t frame_number;
    uint32_t draw_calls;
    uint32_t triangles;
    uint32_t state_changes;
    uint32_t texture_binds;
    uint32_t texture_uploads;
    uint32_t texture_upload_bytes;
    uint32_t dynamic_vertex_bytes;
    uint32_t dynamic_index_bytes;
    uint32_t multipass_draws;
    uint32_t fallback_draws;
    uint32_t unsupported_materials;
    uint32_t invalid_draws;
    uint32_t ring_stalls;
    uint32_t gpu_waits;
    uint32_t vblank_waits;
    size_t texture_resident_bytes;
    size_t texture_peak_bytes;
} r_xbox_stats_t;

void R_Xbox_StatsBeginFrame(void);
void R_Xbox_StatsResetAll(void);
r_xbox_stats_t *R_Xbox_StatsMutable(void);
const r_xbox_stats_t *R_Xbox_GetStats(void);
void R_Xbox_StatsWarnOnce(uint32_t reason_bit, const char *message);

#endif
