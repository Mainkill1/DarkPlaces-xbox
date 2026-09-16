/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native framebuffer/event owner for the real engine's bring-up profile.
 * The client stays unavailable until a native renderer exists. In particular,
 * do not select GL32/GLES2 or return dummy GL entry points to pass startup.
 */
#include <SDL.h>
#include "quakedef.h"
#include "xbox/controller_sdl.h"
#include "xbox/attract_policy.h"
#include "xbox/platform/platform.h"

int cl_available = false;
qbool vid_supportrefreshrate = false;
static dp_button_gate_t input_gate;
static qbool controller_initialized;

void VID_Init(void)
{
    DP_XboxStage("bootstrap-video");
    Con_Print("XBOX_BOOTSTRAP_VIDEO: framebuffer diagnostics only, no game renderer\n");
}
void VID_Shutdown(void) { DP_ControllerSDL_Shutdown(); controller_initialized = false; }
void VID_Finish(void) { }
qbool VID_InitMode(const viddef_mode_t *mode) { (void)mode; return false; }
size_t VID_ListModes(vid_mode_t *modes, size_t maximum) { (void)modes; (void)maximum; return 0; }
void *GL_GetProcAddress(const char *name) { (void)name; return NULL; }
qbool GL_ExtensionSupported(const char *name) { (void)name; return false; }
void VID_BuildJoyState(vid_joystate_t *state) { memset(state, 0, sizeof(*state)); }
void IN_Move(void) { }

void Sys_SDL_HandleEvents(void)
{
    SDL_Event event;
    dp_pad_sample_t sample;
    uint32_t pressed;
    if (!controller_initialized) {
        controller_initialized = DP_ControllerSDL_Init() == 0;
        DP_ButtonGate_Reset(&input_gate);
    }
    while (SDL_PollEvent(&event)) {
        if (event.type == SDL_QUIT) host.state = host_shutdown;
    }
    if (!controller_initialized) return;
    DP_ControllerSDL_Poll(&sample);
    pressed = DP_ButtonGate_Update(&input_gate, sample.connected != 0, sample.instance, sample.buttons);
    /* Bootstrap controls are intentionally not normal gameplay bindings. */
    if (pressed & (1u << DP_PAD_X))
        Con_Printf("XBOX_GAME_CORE_ALIVE frames=%u time=%.3f controller=%s\n",
            host.framecount, host.realtime, DP_ControllerSDL_Name());
    if (pressed & (1u << DP_PAD_BACK)) host.state = host_shutdown;
}
