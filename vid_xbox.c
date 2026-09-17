/* SPDX-License-Identifier: GPL-2.0-or-later
 * Original Xbox video, controller and frame-presentation owner for the native
 * DarkPlaces renderer. OpenGL/GLES entry points are deliberately unavailable.
 */
#include <SDL.h>
#include <hal/video.h>
#include <pbkit/pbkit.h>

#include "quakedef.h"
#include "cl_attract.h"
#include "r_xbox_backend.h"
#include "xbox/attract_policy.h"
#include "xbox/controller_sdl.h"
#include "xbox/platform/platform.h"

/* Host_Init checks this before VID_Init runs. It therefore describes whether
 * a client was compiled into this executable, not whether video init succeeded. */
int cl_available = true;
qbool vid_supportrefreshrate = true;

static const vid_mode_t xbox_modes[] =
{
    {640, 480, 32, 60, 1, 1}
};

typedef struct xbox_video_state_s
{
    qbool video_mode_set;
    qbool pbkit_initialized;
    qbool backend_initialized;
    qbool controller_initialized;
    qbool runtime_ready;
    dp_button_gate_t normal_input_gate;
} xbox_video_state_t;

static xbox_video_state_t xbox_video;

static qbool VID_XboxModeSupported(const viddef_mode_t *mode)
{
    if (mode == NULL)
        return false;
    if (!mode->fullscreen || mode->display != 0)
        return false;
    if (mode->stereobuffer || mode->samples > 1)
        return false;
    if (mode->bitsperpixel != 32)
        return false;
    if (mode->width != 640 || mode->height != 480)
        return false;
    if (mode->refreshrate != 0 && mode->refreshrate != 60)
        return false;
    return true;
}

static void VID_XboxSetControllerStatus(const dp_pad_sample_t *sample)
{
    const int connected = sample != NULL && sample->connected != 0;

    if (joy_detected.integer != connected)
        Cvar_SetValueQuick(&joy_detected, connected);
    if (joy_active.integer != connected)
    {
        Cvar_SetValueQuick(&joy_active, connected);
        Con_Printf("XBOX_CONTROLLER %s: %s\n",
                   connected ? "connected" : "disconnected",
                   connected ? DP_ControllerSDL_Name() : "none");
    }
}

static void VID_XboxNeutralJoyState(vid_joystate_t *state)
{
    memset(state, 0, sizeof(*state));
    state->is360 = true;
}

static void VID_XboxCopyJoyState(const dp_pad_sample_t *sample,
                                 vid_joystate_t *state)
{
    unsigned int i;

    VID_XboxNeutralJoyState(state);
    if (sample == NULL || !sample->connected)
        return;

    for (i = 0; i < 16u; ++i)
        state->button[i] = (sample->buttons & (1u << i)) != 0u;
    for (i = 0; i < 6u; ++i)
        state->axis[i] = bound(-1.0f, sample->axis[i], 1.0f);

    /* Match the engine's logical XInput layout for controller-only menus. */
    state->button[16] = sample->axis[1] < -0.55f;
    state->button[17] = sample->axis[1] >  0.55f;
    state->button[18] = sample->axis[0] < -0.55f;
    state->button[19] = sample->axis[0] >  0.55f;
    state->button[20] = sample->axis[3] < -0.55f;
    state->button[21] = sample->axis[3] >  0.55f;
    state->button[22] = sample->axis[2] < -0.55f;
    state->button[23] = sample->axis[2] >  0.55f;
}

static void VID_XboxResetRuntimeState(void)
{
    xbox_video.runtime_ready = false;
    vid_hidden = true;
    vid_activewindow = false;
    memset(&vid.mode, 0, sizeof(vid.mode));
}

static void VID_XboxCleanupMode(void)
{
    xbox_video.runtime_ready = false;

    if (xbox_video.backend_initialized)
    {
        R_Xbox_Shutdown();
        xbox_video.backend_initialized = false;
    }
    if (xbox_video.pbkit_initialized)
    {
        pb_kill();
        xbox_video.pbkit_initialized = false;
    }

    xbox_video.video_mode_set = false;
    DP_XboxSetDebugVideo(0);
    VID_XboxResetRuntimeState();
}

qbool VID_HasScreenKeyboardSupport(void)
{
    return false;
}

void VID_ShowKeyboard(qbool show)
{
    (void)show;
}

qbool VID_ShowingKeyboard(void)
{
    return false;
}

void VID_EnableJoystick(qbool enable)
{
    if (enable)
    {
        if (!xbox_video.controller_initialized)
        {
            if (DP_ControllerSDL_Init() < 0)
            {
                Con_Printf(CON_ERROR "XBOX_CONTROLLER initialization failed: %s\n",
                           SDL_GetError());
                return;
            }
            xbox_video.controller_initialized = true;
            DP_ButtonGate_Reset(&xbox_video.normal_input_gate);
        }
    }
    else if (xbox_video.controller_initialized)
    {
        DP_ControllerSDL_Shutdown();
        xbox_video.controller_initialized = false;
        DP_ButtonGate_Reset(&xbox_video.normal_input_gate);
        Cvar_SetValueQuick(&joy_active, 0);
        Cvar_SetValueQuick(&joy_detected, 0);
        Key_ReleaseAll();
        VID_XboxNeutralJoyState(&vid_joystate);
    }
}

void VID_BuildJoyState(vid_joystate_t *state)
{
    dp_pad_sample_t sample;

    if (state == NULL)
        return;

    VID_XboxNeutralJoyState(state);
    if (!xbox_video.controller_initialized)
        return;

    DP_ControllerSDL_Poll(&sample);
    VID_XboxSetControllerStatus(&sample);

    if (CL_Attract_Enabled())
    {
        DP_ButtonGate_Reset(&xbox_video.normal_input_gate);
        CL_Attract_Controller(&sample, state);
        return;
    }

    (void)DP_ButtonGate_Update(&xbox_video.normal_input_gate,
                               sample.connected != 0,
                               sample.instance,
                               sample.buttons);
    if (!xbox_video.normal_input_gate.armed)
        return;

    VID_XboxCopyJoyState(&sample, state);
}

void IN_Move(void)
{
    vid_joystate_t state;

    VID_BuildJoyState(&state);
    VID_ApplyJoyState(&state);
}

void Sys_SDL_HandleEvents(void)
{
    SDL_Event event;

    VID_EnableJoystick(true);
    while (SDL_PollEvent(&event))
    {
        if (event.type == SDL_QUIT)
            host.state = host_shutdown;
    }
}

void VID_Init(void)
{
    Cvar_SetValueQuick(&joy_enable, 1);
    Cvar_SetValueQuick(&vid_fullscreen, 1);
    Cvar_SetValueQuick(&vid_width, 640);
    Cvar_SetValueQuick(&vid_height, 480);
    Cvar_SetValueQuick(&vid_bitsperpixel, 32);
    Cvar_SetValueQuick(&vid_samples, 1);
    Cvar_SetValueQuick(&vid_stereobuffer, 0);
    Cvar_SetValueQuick(&vid_touchscreen_supportshowkeyboard, 0);

    VID_EnableJoystick(true);
    if (!xbox_video.controller_initialized)
        Sys_Error("Original Xbox controller subsystem failed to initialize");
}

qbool VID_InitMode(const viddef_mode_t *mode)
{
    VIDEO_MODE actual_mode;
    int pb_status;

    if (!VID_XboxModeSupported(mode))
    {
        Con_Printf(CON_ERROR
                   "Unsupported Xbox video mode: display=%d fullscreen=%d "
                   "%dx%d %dbpp %.2fhz stereo=%d samples=%d\n",
                   mode ? mode->display : -1,
                   mode ? mode->fullscreen : 0,
                   mode ? mode->width : 0,
                   mode ? mode->height : 0,
                   mode ? mode->bitsperpixel : 0,
                   mode ? mode->refreshrate : 0.0f,
                   mode ? mode->stereobuffer : 0,
                   mode ? mode->samples : 0);
        return false;
    }

    VID_XboxCleanupMode();
    VID_EnableJoystick(true);
    if (!xbox_video.controller_initialized)
        return false;

    DP_XboxStage("nv2a-video-mode");
    if (!XVideoSetMode(640, 480, 32, REFRESH_DEFAULT))
    {
        Con_Print(CON_ERROR "XVideoSetMode failed for 640x480x32\n");
        DP_XboxStage("nv2a-video-mode-failed");
        return false;
    }
    xbox_video.video_mode_set = true;

    pb_status = pb_init();
    if (pb_status != 0)
    {
        Con_Printf(CON_ERROR "pb_init failed with status %d\n", pb_status);
        DP_XboxStage("nv2a-pbkit-failed");
        VID_XboxCleanupMode();
        return false;
    }
    xbox_video.pbkit_initialized = true;

    actual_mode = XVideoGetMode();
    vid.mode.display = 0;
    vid.mode.fullscreen = true;
    vid.mode.desktopfullscreen = false;
    vid.mode.width = (int)pb_back_buffer_width();
    vid.mode.height = (int)pb_back_buffer_height();
    vid.mode.bitsperpixel = actual_mode.bpp ? actual_mode.bpp : 32;
    vid.mode.refreshrate = actual_mode.refresh;
    vid.mode.stereobuffer = false;
    vid.mode.samples = 1;

    memset(&vid.support, 0, sizeof(vid.support));
    vid.renderpath = RENDERPATH_XBOX;
    vid.stencil = true;
    vid.sRGB2D = false;
    vid.sRGB3D = false;
    vid.sRGBcapable2D = false;
    vid.sRGBcapable3D = false;
    vid.allowalphatocoverage = false;
    vid.maxtexturesize_2d = 2048;
    vid.maxtexturesize_3d = 0;
    vid.maxtexturesize_cubemap = 512;
    vid.max_anisotropy = 1;
    vid.maxdrawbuffers = 1;
    vid.forcetextype = TEXTYPE_BGRA;

    gl_vendor = "NVIDIA";
    gl_renderer = "NV2A";
    gl_version = "native-nv2a";
    Cvar_SetQuick(&gl_info_vendor, gl_vendor);
    Cvar_SetQuick(&gl_info_renderer, gl_renderer);
    Cvar_SetQuick(&gl_info_version, gl_version);
    Cvar_SetQuick(&gl_info_extensions, "");
    Cvar_SetQuick(&gl_info_driver, "nxdk/pbkit");

    if (!R_Xbox_Init(&vid.mode))
    {
        Con_Print(CON_ERROR "Native NV2A backend initialization failed\n");
        DP_XboxStage("nv2a-backend-failed");
        VID_XboxCleanupMode();
        return false;
    }
    xbox_video.backend_initialized = true;

    vid_hidden = false;
    vid_activewindow = true;
    xbox_video.runtime_ready = true;
    DP_XboxSetDebugVideo(0);
    DP_XboxStage("nv2a-presentation-ready");
    Con_Printf("Native NV2A video ready: %dx%d %dbpp %dhz\n",
               vid.mode.width, vid.mode.height, vid.mode.bitsperpixel,
               (int)vid.mode.refreshrate);
    return true;
}

void VID_Shutdown(void)
{
    VID_XboxCleanupMode();
    VID_EnableJoystick(false);
}

void VID_Finish(void)
{
    if (!xbox_video.runtime_ready || vid_hidden)
        return;

    VID_UpdateGamma();
    if (!R_Xbox_FrameActive())
        R_Xbox_BeginFrame();
    R_Xbox_EndFrame(vid_vsync.integer != 0 && !cls.timedemo);
}

vid_mode_t VID_GetDesktopMode(void)
{
    vid_mode_t mode = xbox_modes[0];

    if (vid.mode.width > 0)
    {
        mode.width = vid.mode.width;
        mode.height = vid.mode.height;
        mode.bpp = vid.mode.bitsperpixel;
        mode.refreshrate = (int)vid.mode.refreshrate;
    }
    return mode;
}

size_t VID_ListModes(vid_mode_t *modes, size_t maximum)
{
    if (modes == NULL || maximum == 0)
        return 0;
    modes[0] = xbox_modes[0];
    return 1;
}

void *GL_GetProcAddress(const char *name)
{
    (void)name;
    return NULL;
}

qbool GL_ExtensionSupported(const char *name)
{
    (void)name;
    return false;
}
