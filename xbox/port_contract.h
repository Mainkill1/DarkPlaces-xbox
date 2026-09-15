#ifndef DP_XBOX_PORT_CONTRACT_H
#define DP_XBOX_PORT_CONTRACT_H

#include <stdint.h>

#include "config_xbox.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum dp_xbox_boot_stage_e
{
    DP_XBOX_BOOT_ENTRY = 0,
    DP_XBOX_BOOT_BUILD_MANIFEST,
    DP_XBOX_BOOT_MEMORY,
    DP_XBOX_BOOT_COMMANDS,
    DP_XBOX_BOOT_FILESYSTEM,
    DP_XBOX_BOOT_HOST_INIT,
    DP_XBOX_BOOT_STARTUP_CONFIG,
    DP_XBOX_BOOT_SMOKE_COMMAND,
    DP_XBOX_BOOT_STABLE_IDLE,
    DP_XBOX_BOOT_FATAL,
    DP_XBOX_BOOT_STAGE_COUNT
} dp_xbox_boot_stage_t;

typedef struct dp_xbox_port_capabilities_s
{
    const char *profile_name;
    const char *source_revision;
    const char *nxdk_revision;
    uint32_t memory_target_mib;
    unsigned int renderer;
    unsigned int audio;
    unsigned int network;
    unsigned int dynamic_loading;
    unsigned int filesystem_write;
    unsigned int controller_input;
} dp_xbox_port_capabilities_t;

const char *DP_XboxBootStageName(dp_xbox_boot_stage_t stage);
const dp_xbox_port_capabilities_t *DP_XboxPortCapabilities(void);

#ifdef __cplusplus
}
#endif

#endif
