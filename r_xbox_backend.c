/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <pbkit/pbkit.h>
#include <windows.h>

#include "quakedef.h"
#include "r_xbox_backend.h"
#include "r_xbox_stats.h"
#include "xbox/platform/platform.h"

#define R_XBOX_GPU_TIMEOUT_MS 2000u

typedef struct r_xbox_device_s
{
    qbool initialized;
    qbool frame_active;
    uint32_t state_generation;
    int width;
    int height;
    r_xbox_init_stage_t completed_stage;
} r_xbox_device_t;

static r_xbox_device_t r_xbox_device;

static void R_Xbox_WaitForGpuIdle(const char *stage)
{
    DWORD start = GetTickCount();
    qbool counted = false;

    while (pb_busy())
    {
        if (!counted)
        {
            R_Xbox_StatsMutable()->gpu_waits++;
            counted = true;
        }
        if ((DWORD)(GetTickCount() - start) >= R_XBOX_GPU_TIMEOUT_MS)
            Sys_Error("NV2A timeout while waiting for %s", stage);
        Sleep(0);
    }
}

static void R_Xbox_QueuePresent(void)
{
    DWORD start = GetTickCount();

    while (pb_finished())
    {
        if ((DWORD)(GetTickCount() - start) >= R_XBOX_GPU_TIMEOUT_MS)
            Sys_Error("NV2A timeout while queueing frame presentation");
        pb_wait_for_vbl();
        R_Xbox_StatsMutable()->vblank_waits++;
    }
}

qbool R_Xbox_Init(const viddef_mode_t *mode)
{
    if (mode == NULL || mode->width <= 0 || mode->height <= 0)
        return false;
    if ((int)pb_back_buffer_width() != mode->width ||
        (int)pb_back_buffer_height() != mode->height)
        return false;

    memset(&r_xbox_device, 0, sizeof(r_xbox_device));
    R_Xbox_StatsResetAll();

    r_xbox_device.width = mode->width;
    r_xbox_device.height = mode->height;
    r_xbox_device.completed_stage = R_XBOX_INIT_TARGETS;
    r_xbox_device.initialized = true;

    pb_show_front_screen();
    R_Xbox_InvalidateState();
    DP_XboxStage("nv2a-backend-ready");
    return true;
}

void R_Xbox_Shutdown(void)
{
    if (!r_xbox_device.initialized)
        return;

    r_xbox_device.frame_active = false;
    r_xbox_device.initialized = false;
    r_xbox_device.completed_stage = R_XBOX_INIT_NONE;
    r_xbox_device.state_generation = 0u;
}

void R_Xbox_InvalidateState(void)
{
    if (r_xbox_device.state_generation != UINT32_MAX)
        r_xbox_device.state_generation++;
}

void R_Xbox_BeginFrame(void)
{
    if (!r_xbox_device.initialized || r_xbox_device.frame_active)
        return;

    R_Xbox_StatsBeginFrame();
    pb_reset();
    pb_target_back_buffer();
    R_Xbox_InvalidateState();
    r_xbox_device.frame_active = true;
}

void R_Xbox_EndFrame(qbool wait_for_vblank)
{
    if (!r_xbox_device.initialized)
        return;

    if (!r_xbox_device.frame_active)
        R_Xbox_BeginFrame();

    R_Xbox_WaitForGpuIdle("frame completion");
    R_Xbox_QueuePresent();
    if (wait_for_vblank)
    {
        pb_wait_for_vbl();
        R_Xbox_StatsMutable()->vblank_waits++;
    }
    r_xbox_device.frame_active = false;
}

qbool R_Xbox_IsInitialized(void)
{
    return r_xbox_device.initialized;
}

qbool R_Xbox_FrameActive(void)
{
    return r_xbox_device.frame_active;
}

r_xbox_init_stage_t R_Xbox_CompletedStage(void)
{
    return r_xbox_device.completed_stage;
}
