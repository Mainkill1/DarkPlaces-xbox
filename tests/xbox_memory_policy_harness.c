#include <assert.h>
#include <stdint.h>
#include <string.h>

#include "xbox_memory_policy.h"

#define MIB ((uint64_t)1024 * 1024)

static xbox_memory_policy_t select_policy(uint64_t mib, const char *request,
	                                         xbox_memory_select_status_t expected)
{
	xbox_memory_policy_t policy;
	assert(Xbox_MemoryPolicySelect(mib * MIB, request, &policy) == expected);
	return policy;
}

int main(void)
{
	xbox_memory_policy_t policy;
	xbox_memory_runtime_values_t values;

	policy = select_policy(64, "auto", XBOX_MEMORY_SELECT_OK);
	assert(policy.profile == XBOX_MEMORY_PROFILE_RETAIL64);
	assert(!strcmp(policy.name, "retail64"));
	policy = select_policy(80, "auto", XBOX_MEMORY_SELECT_OK);
	assert(policy.profile == XBOX_MEMORY_PROFILE_RETAIL64);
	policy = select_policy(111, "auto", XBOX_MEMORY_SELECT_OK);
	assert(policy.profile == XBOX_MEMORY_PROFILE_RETAIL64);
	policy = select_policy(112, "auto", XBOX_MEMORY_SELECT_OK);
	assert(policy.profile == XBOX_MEMORY_PROFILE_DEV128);
	policy = select_policy(128, "auto", XBOX_MEMORY_SELECT_OK);
	assert(policy.profile == XBOX_MEMORY_PROFILE_DEV128);
	assert(!strcmp(policy.name, "dev128"));

	policy = select_policy(128, "retail64", XBOX_MEMORY_SELECT_OK);
	assert(policy.profile == XBOX_MEMORY_PROFILE_RETAIL64);
	policy = select_policy(128, "xemu64", XBOX_MEMORY_SELECT_OK);
	assert(policy.profile == XBOX_MEMORY_PROFILE_XEMU64);
	assert(policy.enforce_retail_ceilings);
	policy = select_policy(64, "dev128", XBOX_MEMORY_SELECT_DEV128_UNAVAILABLE);
	assert(policy.profile == XBOX_MEMORY_PROFILE_RETAIL64);
	assert(Xbox_MemoryPolicySelect(128 * MIB, "broken", &policy) ==
	       XBOX_MEMORY_SELECT_INVALID_REQUEST);

	policy = select_policy(64, "auto", XBOX_MEMORY_SELECT_OK);
	values.gl_max_size = 2048;
	values.gl_picmip = 1;
	values.r_picmipworld = 0;
	values.r_precachetextures = 2;
	values.snd_precache = 1;
	values.snd_streaming = 0;
	Xbox_MemoryPolicyClamp(&policy, &values);
	assert(values.gl_max_size == 1024);
	assert(values.gl_picmip == 2);
	assert(values.r_picmipworld == 1);
	assert(values.r_precachetextures == 1);
	assert(values.snd_precache == 0);
	assert(values.snd_streaming == 1);

	values.gl_max_size = 512;
	values.gl_picmip = 2;
	values.r_picmipworld = 2;
	values.r_precachetextures = 0;
	values.snd_precache = 0;
	values.snd_streaming = 1;
	Xbox_MemoryPolicyClamp(&policy, &values);
	assert(values.gl_max_size == 512);
	assert(values.gl_picmip == 2);
	assert(values.r_picmipworld == 2);
	assert(values.r_precachetextures == 1);
	assert(values.snd_precache == 0);
	assert(values.snd_streaming == 1);

	policy = select_policy(128, "auto", XBOX_MEMORY_SELECT_OK);
	values.gl_max_size = 1536;
	values.gl_picmip = 2;
	values.r_picmipworld = 0;
	values.r_precachetextures = 2;
	values.snd_precache = 0;
	values.snd_streaming = 0;
	Xbox_MemoryPolicyClamp(&policy, &values);
	assert(values.gl_max_size == 1536);
	assert(values.gl_picmip == 2);
	assert(values.r_picmipworld == 0);
	assert(values.r_precachetextures == 2);
	assert(values.snd_precache == 0);
	assert(values.snd_streaming == 0);

	return 0;
}
