#include <hal/debug.h>
#include <hal/video.h>
#include <windows.h>

#include "port_contract.h"

static const char *DP_XboxCapabilityState(unsigned int enabled)
{
    return enabled ? "enabled" : "disabled";
}

static void DP_XboxDrawFoundationScreen(DWORD elapsed_ms)
{
    const dp_xbox_port_capabilities_t *caps = DP_XboxPortCapabilities();

    debugClearScreen();
    debugPrint("DarkPlaces Original Xbox foundation\n");
    debugPrint("marker=%s\n", DP_XboxBootStageName(DP_XBOX_BOOT_ENTRY));
    debugPrint("marker=%s\n", DP_XboxBootStageName(DP_XBOX_BOOT_STABLE_IDLE));
    debugPrint("profile=%s\n", caps->profile_name);
    debugPrint("source=%s\n", caps->source_revision);
    debugPrint("nxdk=%s\n", caps->nxdk_revision);
    debugPrint("memory-target=%lu MiB\n", (unsigned long)caps->memory_target_mib);
    debugPrint("renderer=%s audio=%s network=%s\n",
               DP_XboxCapabilityState(caps->renderer),
               DP_XboxCapabilityState(caps->audio),
               DP_XboxCapabilityState(caps->network));
    debugPrint("dynamic-loading=%s filesystem-write=%s controller=%s\n",
               DP_XboxCapabilityState(caps->dynamic_loading),
               DP_XboxCapabilityState(caps->filesystem_write),
               DP_XboxCapabilityState(caps->controller_input));
    debugPrint("uptime-ms=%lu\n", (unsigned long)elapsed_ms);
    debugPrint("XBOX_FOUNDATION_READY\n");
    debugPrint("This is a toolchain smoke target, not the DarkPlaces engine.\n");
}

int main(void)
{
    DWORD start_ms;

    XVideoSetMode(640, 480, 32, REFRESH_DEFAULT);
    start_ms = GetTickCount();

    for (;;)
    {
        DWORD elapsed_ms = GetTickCount() - start_ms;
        DP_XboxDrawFoundationScreen(elapsed_ms);
        Sleep(1000);
    }

    return 0;
}
