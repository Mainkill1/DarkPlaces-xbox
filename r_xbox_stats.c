/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <string.h>

#include "quakedef.h"
#include "r_xbox_stats.h"

static r_xbox_stats_t r_xbox_stats;
static uint32_t r_xbox_warned_reasons;

void R_Xbox_StatsBeginFrame(void)
{
    const uint32_t frame_number = r_xbox_stats.frame_number + 1u;
    const size_t resident_bytes = r_xbox_stats.texture_resident_bytes;
    const size_t peak_bytes = r_xbox_stats.texture_peak_bytes;

    memset(&r_xbox_stats, 0, sizeof(r_xbox_stats));
    r_xbox_stats.frame_number = frame_number;
    r_xbox_stats.texture_resident_bytes = resident_bytes;
    r_xbox_stats.texture_peak_bytes = peak_bytes;
}

void R_Xbox_StatsResetAll(void)
{
    memset(&r_xbox_stats, 0, sizeof(r_xbox_stats));
    r_xbox_warned_reasons = 0u;
}

r_xbox_stats_t *R_Xbox_StatsMutable(void)
{
    return &r_xbox_stats;
}

const r_xbox_stats_t *R_Xbox_GetStats(void)
{
    return &r_xbox_stats;
}

void R_Xbox_StatsWarnOnce(uint32_t reason_bit, const char *message)
{
    if (reason_bit == 0u || message == NULL || message[0] == '\0')
        return;

    if ((r_xbox_warned_reasons & reason_bit) != 0u)
        return;

    r_xbox_warned_reasons |= reason_bit;
    Con_Printf("XBOX_RENDERER_FALLBACK reason=0x%08x %s\n",
               (unsigned int)reason_bit, message);
}
