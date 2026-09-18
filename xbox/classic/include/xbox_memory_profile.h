#ifndef XBOX_MEMORY_PROFILE_H
#define XBOX_MEMORY_PROFILE_H

#include <stdint.h>

#include "xbox_memory_policy.h"

int Xbox_MemoryProfileInitialize(const char *override_path);
const xbox_memory_policy_t *Xbox_MemoryProfilePolicy(void);
int Xbox_MemoryProfileAllowsEnhancedMaterialLayers(void);
void Xbox_MemoryProfileRegisterCommands(void);
void Xbox_MemoryTraceLoadFailure(const char *path, int64_t expected,
	int64_t actual);
void Xbox_MemoryTraceTextureUpload(const char *operation, const char *phase,
	int level, int width, int height);

#endif
