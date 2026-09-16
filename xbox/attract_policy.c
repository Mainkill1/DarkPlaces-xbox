/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "attract_policy.h"
#include <limits.h>
#include <string.h>

void DP_Attract_Init(dp_attract_t *s) { memset(s, 0, sizeof(*s)); }
bool DP_Attract_Active(const dp_attract_t *s)
{
    return s->state == DP_ATTRACT_READY || s->state == DP_ATTRACT_LOADING || s->state == DP_ATTRACT_PLAYING;
}
bool DP_Attract_Start(dp_attract_t *s, unsigned count)
{
    DP_Attract_Init(s);
    if (!count || count > DP_ATTRACT_MAX_DEMOS) {
        s->state = DP_ATTRACT_FAILED;
        return false;
    }
    s->count = count;
    s->state = DP_ATTRACT_READY;
    return true;
}
bool DP_Attract_TakeNext(dp_attract_t *s, unsigned *index)
{
    if (s->state != DP_ATTRACT_READY) return false;
    *index = s->index;
    s->state = DP_ATTRACT_LOADING;
    return true;
}
void DP_Attract_Loaded(dp_attract_t *s, bool success)
{
    if (s->state == DP_ATTRACT_LOADING)
        s->state = success ? DP_ATTRACT_PLAYING : DP_ATTRACT_FAILED;
}
void DP_Attract_Ended(dp_attract_t *s, bool success)
{
    if (s->state != DP_ATTRACT_PLAYING) return;
    if (!success) { s->state = DP_ATTRACT_FAILED; return; }
    if (++s->index == s->count) {
        s->index = 0;
        if (s->loops != UINT64_MAX) ++s->loops;
    }
    s->state = DP_ATTRACT_READY;
}
void DP_Attract_Stop(dp_attract_t *s) { s->state = DP_ATTRACT_MANUAL; }
void DP_Attract_Fail(dp_attract_t *s) { s->state = DP_ATTRACT_FAILED; }
void DP_ButtonGate_Reset(dp_button_gate_t *g) { memset(g, 0, sizeof(*g)); }
uint32_t DP_ButtonGate_Update(dp_button_gate_t *g, bool connected, int32_t instance, uint32_t buttons)
{
    uint32_t pressed;
    if (!connected) { DP_ButtonGate_Reset(g); return 0; }
    if (!g->connected || g->instance != instance) {
        DP_ButtonGate_Reset(g);
        g->connected = true;
        g->instance = instance;
    }
    if (!g->armed) {
        if (!buttons) g->armed = true;
        g->previous = buttons;
        return 0;
    }
    pressed = buttons & ~g->previous;
    g->previous = buttons;
    return pressed;
}
bool DP_DemoPathValid(const char *path)
{
    size_t i, n;
    if (!path) return false;
    n = strlen(path);
    if (n < 5 || n >= DP_ATTRACT_MAX_PATH || path[0] == '/' || strcmp(path + n - 4, ".dem")) return false;
    if (strstr(path, "..") || strstr(path, "//") || strstr(path, "/./")) return false;
    for (i = 0; i < n; ++i) {
        unsigned char c = (unsigned char)path[i];
        if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') ||
              c == '_' || c == '-' || c == '/' || c == '.')) return false;
    }
    return path[0] != '.';
}
bool DP_DemoTrackHeader(const char *data, size_t size, int *track, size_t *consumed)
{
    size_t i = 0, digits = 0;
    uint64_t value = 0, limit;
    bool negative;
    if (!data || !size) return false;
    negative = data[0] == '-';
    if (negative) ++i;
    limit = negative ? (uint64_t)INT_MAX + 1 : INT_MAX;
    for (; i < size && i < 16; ++i) {
        unsigned char c = (unsigned char)data[i];
        if (c == '\r' && i + 1 < size && data[i + 1] == '\n') { ++i; c = '\n'; }
        if (c == '\n') {
            if (!digits) return false;
            *track = negative ? (int)(-(int64_t)value) : (int)value;
            *consumed = i + 1;
            return true;
        }
        if (c < '0' || c > '9' || value > (limit - (c - '0')) / 10) return false;
        value = value * 10 + (c - '0');
        ++digits;
    }
    return false;
}
