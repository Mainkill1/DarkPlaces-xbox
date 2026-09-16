/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef DP_CONTROLLER_SDL_H
#define DP_CONTROLLER_SDL_H
#include <stdint.h>
/* Fixed layout shared with the engine's X360 logical-key path. It names logical
 * actions, not the physical console generation. No SDL enum counts leak out. */
enum {
    DP_PAD_UP, DP_PAD_DOWN, DP_PAD_LEFT, DP_PAD_RIGHT, DP_PAD_START, DP_PAD_BACK,
    DP_PAD_LSTICK, DP_PAD_RSTICK, DP_PAD_WHITE, DP_PAD_BLACK,
    DP_PAD_A, DP_PAD_B, DP_PAD_X, DP_PAD_Y, DP_PAD_LT, DP_PAD_RT
};
typedef struct {
    int connected;
    int32_t instance;
    uint32_t buttons;
    float axis[6]; /* left X/Y, right X/Y, LT, RT; Y positive is up */
} dp_pad_sample_t;
int DP_ControllerSDL_Init(void);
void DP_ControllerSDL_Shutdown(void);
void DP_ControllerSDL_Poll(dp_pad_sample_t *sample);
const char *DP_ControllerSDL_Name(void);
#endif
