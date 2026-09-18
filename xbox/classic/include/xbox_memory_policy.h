#ifndef XBOX_MEMORY_POLICY_H
#define XBOX_MEMORY_POLICY_H

#include <stdint.h>

typedef enum xbox_memory_profile_e
{
	XBOX_MEMORY_PROFILE_RETAIL64,
	XBOX_MEMORY_PROFILE_DEV128,
	XBOX_MEMORY_PROFILE_XEMU64
} xbox_memory_profile_t;

typedef enum xbox_memory_select_status_e
{
	XBOX_MEMORY_SELECT_OK,
	XBOX_MEMORY_SELECT_DEV128_UNAVAILABLE,
	XBOX_MEMORY_SELECT_INVALID_REQUEST
} xbox_memory_select_status_t;

typedef struct xbox_memory_policy_s
{
	xbox_memory_profile_t profile;
	const char *name;
	uint64_t total_bytes;
	int enforce_retail_ceilings;
} xbox_memory_policy_t;

typedef struct xbox_memory_runtime_values_s
{
	int gl_max_size;
	int gl_picmip;
	int r_precachetextures;
	int snd_precache;
	int snd_streaming;
} xbox_memory_runtime_values_t;

xbox_memory_select_status_t Xbox_MemoryPolicySelect(
	uint64_t total_bytes, const char *request, xbox_memory_policy_t *out);
void Xbox_MemoryPolicyClamp(const xbox_memory_policy_t *policy,
	xbox_memory_runtime_values_t *values);

#endif
