#include "port_contract.h"

static const char *const dp_xbox_boot_stage_names[] =
{
    "entry",
    "build-manifest",
    "memory",
    "commands",
    "filesystem",
    "host-init",
    "startup-config",
    "smoke-command",
    "stable-idle",
    "fatal"
};

#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
_Static_assert(
    sizeof(dp_xbox_boot_stage_names) / sizeof(dp_xbox_boot_stage_names[0]) ==
        DP_XBOX_BOOT_STAGE_COUNT,
    "Xbox boot-stage names must match dp_xbox_boot_stage_t"
);
#endif

static const dp_xbox_port_capabilities_t dp_xbox_foundation_capabilities =
{
    DP_XBOX_PROFILE_NAME,
    DP_XBOX_SOURCE_REVISION,
    DP_XBOX_NXDK_REVISION,
    DP_XBOX_MEMORY_TARGET_MIB,
    DP_XBOX_CAP_RENDERER,
    DP_XBOX_CAP_AUDIO,
    DP_XBOX_CAP_NETWORK,
    DP_XBOX_CAP_DYNAMIC_LOADING,
    DP_XBOX_CAP_FILESYSTEM_WRITE,
    DP_XBOX_CAP_CONTROLLER_INPUT
};

const char *DP_XboxBootStageName(dp_xbox_boot_stage_t stage)
{
    int stage_index = (int)stage;

    if (stage_index < 0 || stage_index >= (int)DP_XBOX_BOOT_STAGE_COUNT)
        return "invalid";

    return dp_xbox_boot_stage_names[stage_index];
}

const dp_xbox_port_capabilities_t *DP_XboxPortCapabilities(void)
{
    return &dp_xbox_foundation_capabilities;
}
