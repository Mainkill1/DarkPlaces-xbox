#include <stddef.h>
#include <string.h>

#include "include/xbox_memory_policy.h"

#define XBOX_DEV128_THRESHOLD_BYTES ((uint64_t)112 * 1024 * 1024)

static void Xbox_MemoryPolicySet(xbox_memory_policy_t *out,
	xbox_memory_profile_t profile, uint64_t total_bytes)
{
	out->profile = profile;
	out->total_bytes = total_bytes;
	out->enforce_retail_ceilings = profile != XBOX_MEMORY_PROFILE_DEV128;
	if (profile == XBOX_MEMORY_PROFILE_DEV128)
		out->name = "dev128";
	else if (profile == XBOX_MEMORY_PROFILE_XEMU64)
		out->name = "xemu64";
	else
		out->name = "retail64";
}

xbox_memory_select_status_t Xbox_MemoryPolicySelect(
	uint64_t total_bytes, const char *request, xbox_memory_policy_t *out)
{
	if (!out)
		return XBOX_MEMORY_SELECT_INVALID_REQUEST;
	if (!request || !request[0] || !strcmp(request, "auto"))
	{
		Xbox_MemoryPolicySet(out,
			total_bytes >= XBOX_DEV128_THRESHOLD_BYTES
				? XBOX_MEMORY_PROFILE_DEV128
				: XBOX_MEMORY_PROFILE_RETAIL64,
			total_bytes);
		return XBOX_MEMORY_SELECT_OK;
	}
	if (!strcmp(request, "retail64"))
	{
		Xbox_MemoryPolicySet(out, XBOX_MEMORY_PROFILE_RETAIL64, total_bytes);
		return XBOX_MEMORY_SELECT_OK;
	}
	if (!strcmp(request, "xemu64"))
	{
		Xbox_MemoryPolicySet(out, XBOX_MEMORY_PROFILE_XEMU64, total_bytes);
		return XBOX_MEMORY_SELECT_OK;
	}
	if (!strcmp(request, "dev128"))
	{
		if (total_bytes < XBOX_DEV128_THRESHOLD_BYTES)
		{
			Xbox_MemoryPolicySet(out, XBOX_MEMORY_PROFILE_RETAIL64, total_bytes);
			return XBOX_MEMORY_SELECT_DEV128_UNAVAILABLE;
		}
		Xbox_MemoryPolicySet(out, XBOX_MEMORY_PROFILE_DEV128, total_bytes);
		return XBOX_MEMORY_SELECT_OK;
	}
	Xbox_MemoryPolicySet(out, XBOX_MEMORY_PROFILE_RETAIL64, total_bytes);
	return XBOX_MEMORY_SELECT_INVALID_REQUEST;
}

void Xbox_MemoryPolicyClamp(const xbox_memory_policy_t *policy,
	xbox_memory_runtime_values_t *values)
{
	if (!policy || !values || !policy->enforce_retail_ceilings)
		return;
	if (values->gl_max_size > 1024)
		values->gl_max_size = 1024;
	if (values->gl_picmip < 2)
		values->gl_picmip = 2;
	if (values->r_picmipworld < 1)
		values->r_picmipworld = 1;
	if (values->r_precachetextures != 1)
		values->r_precachetextures = 1;
	if (values->snd_precache > 0)
		values->snd_precache = 0;
	if (values->snd_streaming < 1)
		values->snd_streaming = 1;
}
