#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <xboxkrnl/xboxkrnl.h>

#include "quakedef.h"
#include "include/xbox_boot_trace.h"
#include "include/xbox_memory_policy.h"
#include "include/xbox_memory_profile.h"

#define XBOX_MIB ((uint64_t)1024 * 1024)

static xbox_memory_policy_t xbox_memory_policy;

static int Xbox_MemorySnapshot(uint64_t *total_bytes, uint64_t *available_bytes)
{
	MM_STATISTICS statistics;
	memset(&statistics, 0, sizeof(statistics));
	statistics.Length = sizeof(statistics);
	if (MmQueryStatistics(&statistics) < 0)
		return 0;
	*total_bytes = (uint64_t)statistics.TotalPhysicalPages * PAGE_SIZE;
	*available_bytes = (uint64_t)statistics.AvailablePages * PAGE_SIZE;
	return 1;
}

static int Xbox_MemoryReadOverride(const char *path, char *token, size_t token_size)
{
	FILE *file;
	size_t count, begin, end;
	if (!path || !path[0] || token_size < 2)
		return 0;
	file = fopen(path, "rb");
	if (!file)
		return 0;
	count = fread(token, 1, token_size, file);
	if (ferror(file) || (count == token_size && !feof(file)))
	{
		fclose(file);
		return -1;
	}
	fclose(file);
	begin = 0;
	while (begin < count && isspace((unsigned char)token[begin]))
		++begin;
	end = count;
	while (end > begin && isspace((unsigned char)token[end - 1]))
		--end;
	if (end == begin || end - begin >= token_size)
		return -1;
	memmove(token, token + begin, end - begin);
	token[end - begin] = 0;
	return 1;
}

int Xbox_MemoryProfileInitialize(const char *override_path)
{
	char request[32] = "auto";
	uint64_t total_bytes, available_bytes;
	xbox_memory_select_status_t status;
	int override_result;

	if (!Xbox_MemorySnapshot(&total_bytes, &available_bytes))
	{
		Xbox_BootTraceMark("Xbox memory query failed");
		return 0;
	}
	override_result = Xbox_MemoryReadOverride(override_path, request, sizeof(request));
	if (override_result < 0)
	{
		Xbox_BootTraceMark("Xbox memory invalid override; using auto");
		memcpy(request, "auto", sizeof("auto"));
	}
	status = Xbox_MemoryPolicySelect(total_bytes, request, &xbox_memory_policy);
	if (status == XBOX_MEMORY_SELECT_INVALID_REQUEST)
	{
		Xbox_BootTraceMark("Xbox memory invalid override '%s'; using auto", request);
		memcpy(request, "auto", sizeof("auto"));
		status = Xbox_MemoryPolicySelect(total_bytes, request, &xbox_memory_policy);
	}
	if (status == XBOX_MEMORY_SELECT_DEV128_UNAVAILABLE)
		Xbox_BootTraceMark("Xbox memory dev128 unavailable; falling back to retail64");
	Xbox_BootTraceMark(
		"Xbox memory profile=%s request=%s total=%llu MiB available=%llu MiB%s",
		xbox_memory_policy.name, request,
		(unsigned long long)(total_bytes / XBOX_MIB),
		(unsigned long long)(available_bytes / XBOX_MIB),
		xbox_memory_policy.profile == XBOX_MEMORY_PROFILE_DEV128
			? " diagnostic-only" : "");
	return 1;
}

const xbox_memory_policy_t *Xbox_MemoryProfilePolicy(void)
{
	return &xbox_memory_policy;
}

int Xbox_MemoryProfileAllowsEnhancedMaterialLayers(void)
{
	return xbox_memory_policy.profile == XBOX_MEMORY_PROFILE_DEV128
		&& !xbox_memory_policy.enforce_retail_ceilings;
}

int Xbox_MemoryProfileUsesReducedColorTextures(void)
{
	return xbox_memory_policy.profile != XBOX_MEMORY_PROFILE_DEV128
		|| xbox_memory_policy.enforce_retail_ceilings;
}

void Xbox_MemoryTraceLoadFailure(const char *path, int64_t expected,
	int64_t actual)
{
	uint64_t total_bytes, available_bytes;
	if (Xbox_MemorySnapshot(&total_bytes, &available_bytes))
		Xbox_BootTraceMark(
			"Xbox memory load failure path=%s expected=%lld actual=%lld "
			"available_pages=%llu available=%llu MiB",
			path ? path : "(null)", (long long)expected, (long long)actual,
			(unsigned long long)(available_bytes / PAGE_SIZE),
			(unsigned long long)(available_bytes / XBOX_MIB));
	else
		Xbox_BootTraceMark(
			"Xbox memory load failure path=%s expected=%lld actual=%lld "
			"available=unavailable",
			path ? path : "(null)", (long long)expected, (long long)actual);
}

void Xbox_MemoryTraceTextureUpload(const char *operation, const char *phase,
	int level, int width, int height)
{
	uint64_t total_bytes, available_bytes;
	if (Xbox_MemorySnapshot(&total_bytes, &available_bytes))
		Xbox_BootTraceMark(
			"Xbox texture upload operation=%s phase=%s level=%d size=%dx%d "
			"available_pages=%llu",
			operation, phase, level, width, height,
			(unsigned long long)(available_bytes / PAGE_SIZE));
	else
		Xbox_BootTraceMark(
			"Xbox texture upload operation=%s phase=%s level=%d size=%dx%d "
			"available=unavailable",
			operation, phase, level, width, height);
}

void Xbox_MemoryTracePresentedFrame(void)
{
	static unsigned int frames;
	static uint64_t low_water_pages = UINT64_MAX;
	uint64_t total_bytes, available_bytes, available_pages;
	++frames;
	if (frames != 1 && frames % 60 != 0)
		return;
	if (!Xbox_MemorySnapshot(&total_bytes, &available_bytes))
	{
		Xbox_BootTraceMark("Xbox presented frame=%u available=unavailable", frames);
		return;
	}
	available_pages = available_bytes / PAGE_SIZE;
	if (available_pages < low_water_pages)
		low_water_pages = available_pages;
	Xbox_BootTraceMark(
		"Xbox presented frame=%u world_loaded=%d available_pages=%llu "
		"low_water_pages=%llu headroom_20mib=%d",
		frames, cl.worldmodel != NULL,
		(unsigned long long)available_pages,
		(unsigned long long)low_water_pages,
		available_bytes >= 20 * XBOX_MIB);
}

static int Xbox_MemoryReadRuntimeValues(xbox_memory_runtime_values_t *values,
	cvar_t **variables)
{
	static const char *names[] = {
		"gl_max_size", "gl_picmip", "r_picmipworld",
		"r_precachetextures", "snd_precache", "snd_streaming"
	};
	size_t i;
	for (i = 0; i < sizeof(names) / sizeof(names[0]); ++i)
	{
		variables[i] = Cvar_FindVar(names[i]);
		if (!variables[i])
		{
			Xbox_BootTraceMark("Xbox memory profile missing cvar %s", names[i]);
			return 0;
		}
	}
	values->gl_max_size = variables[0]->integer;
	values->gl_picmip = variables[1]->integer;
	values->r_picmipworld = variables[2]->integer;
	values->r_precachetextures = variables[3]->integer;
	values->snd_precache = variables[4]->integer;
	values->snd_streaming = variables[5]->integer;
	return 1;
}

static void Xbox_ApplyMemoryProfile_f(void)
{
	xbox_memory_runtime_values_t before, after, retail_values;
	xbox_memory_policy_t retail_policy;
	cvar_t *variables[6];
	uint64_t total_bytes, available_bytes;
	unsigned int retail_violations = 0;
	int snapshot_available;
	if (!Xbox_MemoryReadRuntimeValues(&before, variables))
		return;
	retail_policy = xbox_memory_policy;
	retail_policy.enforce_retail_ceilings = 1;
	retail_values = before;
	Xbox_MemoryPolicyClamp(&retail_policy, &retail_values);
	retail_violations += retail_values.gl_max_size != before.gl_max_size;
	retail_violations += retail_values.gl_picmip != before.gl_picmip;
	retail_violations += retail_values.r_picmipworld != before.r_picmipworld;
	retail_violations +=
		retail_values.r_precachetextures != before.r_precachetextures;
	retail_violations += retail_values.snd_precache != before.snd_precache;
	retail_violations += retail_values.snd_streaming != before.snd_streaming;
	after = before;
	Xbox_MemoryPolicyClamp(&xbox_memory_policy, &after);
	if (after.gl_max_size != before.gl_max_size)
		Cvar_SetValueQuick(variables[0], (float)after.gl_max_size);
	if (after.gl_picmip != before.gl_picmip)
		Cvar_SetValueQuick(variables[1], (float)after.gl_picmip);
	if (after.r_picmipworld != before.r_picmipworld)
		Cvar_SetValueQuick(variables[2], (float)after.r_picmipworld);
	if (after.r_precachetextures != before.r_precachetextures)
		Cvar_SetValueQuick(variables[3], (float)after.r_precachetextures);
	if (after.snd_precache != before.snd_precache)
		Cvar_SetValueQuick(variables[4], (float)after.snd_precache);
	if (after.snd_streaming != before.snd_streaming)
		Cvar_SetValueQuick(variables[5], (float)after.snd_streaming);
	snapshot_available = Xbox_MemorySnapshot(&total_bytes, &available_bytes);
	if (snapshot_available)
		Xbox_BootTraceMark(
			"Xbox memory applied profile=%s available=%llu MiB "
			"gl_max_size=%d->%d gl_picmip=%d->%d "
			"picmip_world=%d->%d "
			"texture_precache=%d->%d sound_precache=%d->%d "
			"sound_streaming=%d->%d enhanced_material_layers=%d "
			"reduced_color_textures=%d "
			"retail64_ceiling_violations=%u%s",
			xbox_memory_policy.name,
			(unsigned long long)(available_bytes / XBOX_MIB),
			before.gl_max_size, after.gl_max_size,
			before.gl_picmip, after.gl_picmip,
			before.r_picmipworld, after.r_picmipworld,
			before.r_precachetextures, after.r_precachetextures,
			before.snd_precache, after.snd_precache,
			before.snd_streaming, after.snd_streaming,
			Xbox_MemoryProfileAllowsEnhancedMaterialLayers(),
			Xbox_MemoryProfileUsesReducedColorTextures(),
			retail_violations,
			xbox_memory_policy.profile == XBOX_MEMORY_PROFILE_DEV128
				? " diagnostic-only" : "");
	else
		Xbox_BootTraceMark(
			"Xbox memory applied profile=%s available=unavailable "
			"gl_max_size=%d->%d gl_picmip=%d->%d "
			"picmip_world=%d->%d "
			"texture_precache=%d->%d sound_precache=%d->%d "
			"sound_streaming=%d->%d enhanced_material_layers=%d "
			"reduced_color_textures=%d "
			"retail64_ceiling_violations=%u%s",
			xbox_memory_policy.name,
			before.gl_max_size, after.gl_max_size,
			before.gl_picmip, after.gl_picmip,
			before.r_picmipworld, after.r_picmipworld,
			before.r_precachetextures, after.r_precachetextures,
			before.snd_precache, after.snd_precache,
			before.snd_streaming, after.snd_streaming,
			Xbox_MemoryProfileAllowsEnhancedMaterialLayers(),
			Xbox_MemoryProfileUsesReducedColorTextures(),
			retail_violations,
			xbox_memory_policy.profile == XBOX_MEMORY_PROFILE_DEV128
				? " diagnostic-only" : "");
}

static void Xbox_ExpectContentProfile_f(void)
{
	const xbox_memory_policy_t *policy = Xbox_MemoryProfilePolicy();
	const char *expected;
	const char *actual;
	if (Cmd_Argc() != 2)
		Sys_Error("Xbox content profile command requires stock64 or dev128");
	expected = Cmd_Argv(1);
	if (strcmp(expected, "stock64") && strcmp(expected, "dev128"))
		Sys_Error("Xbox content profile is invalid: %s", expected);
	actual = policy->profile == XBOX_MEMORY_PROFILE_DEV128 ? "dev128" : "stock64";
	if (strcmp(expected, actual))
	{
		Xbox_BootTraceMark(
			"Xbox content profile mismatch disc=%s runtime=%s detected=%llu MiB",
			expected, policy->name,
			(unsigned long long)(policy->total_bytes / XBOX_MIB));
		Sys_Error(
			"Xbox content profile mismatch: disc=%s runtime=%s detected=%llu MiB; use stock64 image if the Xbox kernel exposes only 64 MiB",
			expected, policy->name,
			(unsigned long long)(policy->total_bytes / XBOX_MIB));
	}
	Xbox_BootTraceMark("Xbox content profile matched disc=%s runtime=%s",
		expected, policy->name);
}

void Xbox_MemoryProfileRegisterCommands(void)
{
	Cmd_AddCommand("xbox_apply_memory_profile", Xbox_ApplyMemoryProfile_f,
		"apply detected Xbox memory-profile resource ceilings");
	Cmd_AddCommand("xbox_expect_content_profile", Xbox_ExpectContentProfile_f,
		"stop before autoplay if staged content does not match detected memory");
}
