/* SPDX-License-Identifier: GPL-2.0-or-later
 * Links the production input adapter with real nxdk SDL/USB for controller tests.
 * This is NOT the engine and does NOT pretend to render a Nexuiz demo.
 */
#include <hal/debug.h>
#include <hal/video.h>
#include <windows.h>
#include <SDL.h>
#include "xbox/controller_sdl.h"
#include "xbox/attract_policy.h"

int main(void)
{
    dp_button_gate_t gate = {0};
    dp_pad_sample_t sample;
    DWORD last_display = 0;
    int automatic = 1;
    if (!XVideoSetMode(640, 480, 32, REFRESH_DEFAULT)) return 1;
    if (DP_ControllerSDL_Init() < 0) {
        debugPrint("Controller initialization failed: %s\n", SDL_GetError());
        for (;;) Sleep(1000);
    }
    for (;;) {
        uint32_t pressed;
        SDL_Event event;
        while (SDL_PollEvent(&event)) { /* keep the event queue bounded */ }
        DP_ControllerSDL_Poll(&sample);
        pressed = DP_ButtonGate_Update(&gate, sample.connected != 0, sample.instance, sample.buttons);
        if (automatic && pressed) {
            automatic = 0;
            DP_ButtonGate_Reset(&gate);
        } else if (!automatic && (pressed & (1u << DP_PAD_START))) {
            automatic = 1;
            DP_ButtonGate_Reset(&gate);
        }
        if ((DWORD)(GetTickCount() - last_display) >= 100) {
            last_display = GetTickCount();
            debugClearScreen();
            debugPrint("DarkPlaces controller integration check\n");
            debugPrint("INPUT ONLY: no engine, map or rendered demo\n\n");
            debugPrint("State: %s\n", automatic ? "automatic input isolation" : "manual");
            debugPrint("Any new button exits automatic; Start resumes.\n");
            debugPrint("Release buttons after startup or reconnect.\n\n");
            debugPrint("Controller: %s\n", DP_ControllerSDL_Name());
            debugPrint("Connected=%d instance=%ld buttons=%08lx\n", sample.connected,
                       (long)sample.instance, (unsigned long)sample.buttons);
            debugPrint("LX=%d LY=%d RX=%d RY=%d\n", (int)(sample.axis[0]*1000),
                       (int)(sample.axis[1]*1000), (int)(sample.axis[2]*1000), (int)(sample.axis[3]*1000));
            debugPrint("LT=%d RT=%d (axes scaled by 1000)\n", (int)(sample.axis[4]*1000), (int)(sample.axis[5]*1000));
            debugPrint("White=bit8 Black=bit9 A=bit10 B=bit11\n");
            debugPrint("XBOX_CONTROLLER_CHECK_READY\n");
        }
        Sleep(8);
    }
}
