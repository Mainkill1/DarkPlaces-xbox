/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "controller_sdl.h"
#include <SDL.h>
#include <string.h>

static SDL_GameController *controller;
static int initialized;
static uint32_t trigger_buttons;

int DP_ControllerSDL_Init(void)
{
    if (initialized) return initialized > 0 ? 0 : -1;
    if (SDL_InitSubSystem(SDL_INIT_GAMECONTROLLER) < 0) { initialized = -1; return -1; }
    initialized = 1;
    return 0;
}
void DP_ControllerSDL_Shutdown(void)
{
    if (controller) SDL_GameControllerClose(controller);
    controller = NULL;
    trigger_buttons = 0;
    if (initialized > 0) SDL_QuitSubSystem(SDL_INIT_GAMECONTROLLER);
    initialized = 0;
}
const char *DP_ControllerSDL_Name(void)
{
    const char *name = controller ? SDL_GameControllerName(controller) : NULL;
    return name ? name : "none";
}
static float stick(Sint16 value)
{
    return value < 0 ? value * (1.0f / 32768.0f) : value * (1.0f / 32767.0f);
}
void DP_ControllerSDL_Poll(dp_pad_sample_t *s)
{
    static const SDL_GameControllerButton buttons[14] = {
        SDL_CONTROLLER_BUTTON_DPAD_UP, SDL_CONTROLLER_BUTTON_DPAD_DOWN,
        SDL_CONTROLLER_BUTTON_DPAD_LEFT, SDL_CONTROLLER_BUTTON_DPAD_RIGHT,
        SDL_CONTROLLER_BUTTON_START, SDL_CONTROLLER_BUTTON_BACK,
        SDL_CONTROLLER_BUTTON_LEFTSTICK, SDL_CONTROLLER_BUTTON_RIGHTSTICK,
        SDL_CONTROLLER_BUTTON_LEFTSHOULDER, SDL_CONTROLLER_BUTTON_RIGHTSHOULDER,
        SDL_CONTROLLER_BUTTON_A, SDL_CONTROLLER_BUTTON_B, SDL_CONTROLLER_BUTTON_X, SDL_CONTROLLER_BUTTON_Y
    };
    int i;
    memset(s, 0, sizeof(*s));
    if (initialized <= 0) return;
    SDL_GameControllerUpdate();
    if (controller && !SDL_GameControllerGetAttached(controller)) {
        SDL_GameControllerClose(controller);
        controller = NULL;
        trigger_buttons = 0;
        return; /* deliver one neutral frame to release held engine actions */
    }
    if (!controller) {
        for (i = 0; i < SDL_NumJoysticks(); ++i) {
            if (!SDL_IsGameController(i)) continue;
            controller = SDL_GameControllerOpen(i);
            if (controller) break;
        }
        if (!controller) return;
        SDL_GameControllerUpdate();
    }
    s->connected = 1;
    s->instance = SDL_JoystickInstanceID(SDL_GameControllerGetJoystick(controller));
    for (i = 0; i < 14; ++i)
        if (SDL_GameControllerGetButton(controller, buttons[i])) s->buttons |= 1u << i;
    s->axis[0] = stick(SDL_GameControllerGetAxis(controller, SDL_CONTROLLER_AXIS_LEFTX));
    s->axis[1] = -stick(SDL_GameControllerGetAxis(controller, SDL_CONTROLLER_AXIS_LEFTY));
    s->axis[2] = stick(SDL_GameControllerGetAxis(controller, SDL_CONTROLLER_AXIS_RIGHTX));
    s->axis[3] = -stick(SDL_GameControllerGetAxis(controller, SDL_CONTROLLER_AXIS_RIGHTY));
    for (i = 0; i < 2; ++i) {
        Sint16 value = SDL_GameControllerGetAxis(controller, i ? SDL_CONTROLLER_AXIS_TRIGGERRIGHT : SDL_CONTROLLER_AXIS_TRIGGERLEFT);
        uint32_t mask = 1u << (DP_PAD_LT + i);
        s->axis[4 + i] = value > 0 ? value * (1.0f / 32767.0f) : 0;
        /* Hysteresis avoids a stream of repeated button edges near the threshold. */
        if (s->axis[4 + i] >= 0.20f) trigger_buttons |= mask;
        else if (s->axis[4 + i] <= 0.10f) trigger_buttons &= ~mask;
    }
    s->buttons |= trigger_buttons;
}
