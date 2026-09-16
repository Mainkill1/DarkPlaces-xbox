/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef DP_ATTRACT_POLICY_H
#define DP_ATTRACT_POLICY_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define DP_ATTRACT_MAX_DEMOS 8
#define DP_ATTRACT_MAX_PATH 128

typedef enum {
    DP_ATTRACT_OFF, DP_ATTRACT_READY, DP_ATTRACT_LOADING,
    DP_ATTRACT_PLAYING, DP_ATTRACT_MANUAL, DP_ATTRACT_FAILED
} dp_attract_state_t;
typedef struct {
    dp_attract_state_t state;
    unsigned count, index;
    uint64_t loops;
} dp_attract_t;
typedef struct {
    bool connected, armed;
    int32_t instance;
    uint32_t previous;
} dp_button_gate_t;

void DP_Attract_Init(dp_attract_t *s);
bool DP_Attract_Start(dp_attract_t *s, unsigned count);
bool DP_Attract_Active(const dp_attract_t *s);
bool DP_Attract_TakeNext(dp_attract_t *s, unsigned *index);
void DP_Attract_Loaded(dp_attract_t *s, bool success);
void DP_Attract_Ended(dp_attract_t *s, bool success);
void DP_Attract_Stop(dp_attract_t *s);
void DP_Attract_Fail(dp_attract_t *s);
void DP_ButtonGate_Reset(dp_button_gate_t *g);
uint32_t DP_ButtonGate_Update(dp_button_gate_t *g, bool connected, int32_t instance, uint32_t buttons);
bool DP_DemoPathValid(const char *path);
bool DP_DemoTrackHeader(const char *data, size_t size, int *track, size_t *consumed);
#endif
