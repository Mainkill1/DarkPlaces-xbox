#include <assert.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "quakedef.h"
#include "xbox_memory_profile.h"
#include "xboxkrnl/xboxkrnl.h"

#define ARRAY_COUNT(a) (sizeof(a) / sizeof((a)[0]))
#define MIB ((uint64_t)1024 * 1024)

static uint64_t query_total_bytes;
static uint64_t query_available_bytes;
static NTSTATUS query_status;
static unsigned int query_calls;
static unsigned int query_fail_on_call;
static char trace_text[8192];
static size_t trace_used;
static void (*registered_command)(void);

static cvar_t cvars[] = {
	{0, "gl_max_size", "2048", "", 2048, 2048.0f},
	{0, "gl_picmip", "0", "", 0, 0.0f},
	{0, "r_picmipworld", "0", "", 0, 0.0f},
	{0, "r_precachetextures", "2", "", 2, 2.0f},
	{0, "snd_precache", "1", "", 1, 1.0f},
	{0, "snd_streaming", "0", "", 0, 0.0f},
};

NTSTATUS MmQueryStatistics(PMM_STATISTICS statistics)
{
	++query_calls;
	if (query_calls == query_fail_on_call)
		return -1;
	if (query_status < 0)
		return query_status;
	assert(statistics->Length == sizeof(*statistics));
	statistics->TotalPhysicalPages = (ULONG)(query_total_bytes / PAGE_SIZE);
	statistics->AvailablePages = (ULONG)(query_available_bytes / PAGE_SIZE);
	return 0;
}

void Xbox_BootTraceMark(const char *format, ...)
{
	va_list args;
	int written;
	va_start(args, format);
	written = vsnprintf(trace_text + trace_used, sizeof(trace_text) - trace_used,
		format, args);
	va_end(args);
	assert(written >= 0);
	trace_used += (size_t)written;
	assert(trace_used + 1 < sizeof(trace_text));
	trace_text[trace_used++] = '\n';
	trace_text[trace_used] = 0;
}

cvar_t *Cvar_FindVar(const char *name)
{
	size_t i;
	for (i = 0; i < ARRAY_COUNT(cvars); ++i)
		if (!strcmp(cvars[i].name, name))
			return &cvars[i];
	return NULL;
}

void Cvar_SetValueQuick(cvar_t *var, float value)
{
	var->value = value;
	var->integer = (int)value;
}

void Cmd_AddCommand(const char *name, void (*function)(void), const char *description)
{
	assert(!strcmp(name, "xbox_apply_memory_profile"));
	assert(description && description[0]);
	registered_command = function;
}

static void reset(uint64_t total_mib, uint64_t available_mib)
{
	query_total_bytes = total_mib * MIB;
	query_available_bytes = available_mib * MIB;
	query_status = 0;
	query_calls = 0;
	query_fail_on_call = 0;
	trace_used = 0;
	trace_text[0] = 0;
	registered_command = NULL;
	cvars[0].integer = 2048;
	cvars[1].integer = 0;
	cvars[2].integer = 0;
	cvars[3].integer = 2;
	cvars[4].integer = 1;
	cvars[5].integer = 0;
}

static void write_token(const char *path, const char *token)
{
	FILE *file = fopen(path, "wb");
	assert(file);
	assert(fwrite(token, 1, strlen(token), file) == strlen(token));
	assert(fclose(file) == 0);
}

int main(int argc, char **argv)
{
	char path[1024];
	const xbox_memory_policy_t *policy;
	assert(argc == 2);
	assert(snprintf(path, sizeof(path), "%s/profile.txt", argv[1]) > 0);
	remove(path);
	assert(!Xbox_MemoryProfileAllowsEnhancedMaterialLayers());

	reset(64, 19);
	query_status = -1;
	assert(!Xbox_MemoryProfileInitialize(path));
	assert(strstr(trace_text, "query failed"));

	reset(64, 18);
	assert(Xbox_MemoryProfileInitialize(path));
	policy = Xbox_MemoryProfilePolicy();
	assert(policy->profile == XBOX_MEMORY_PROFILE_RETAIL64);
	assert(!Xbox_MemoryProfileAllowsEnhancedMaterialLayers());
	assert(Xbox_MemoryProfileUsesReducedColorTextures());
	assert(strstr(trace_text, "profile=retail64"));
	assert(strstr(trace_text, "total=64 MiB available=18 MiB"));
	Xbox_MemoryProfileRegisterCommands();
	assert(registered_command);
	registered_command();
	assert(cvars[0].integer == 1024);
	assert(cvars[1].integer == 2);
	assert(cvars[2].integer == 1);
	assert(cvars[3].integer == 1);
	assert(cvars[4].integer == 0);
	assert(cvars[5].integer == 1);
	assert(strstr(trace_text, "applied profile=retail64"));
	assert(strstr(trace_text, "gl_max_size=2048->1024"));
	assert(strstr(trace_text, "gl_picmip=0->2"));
	assert(strstr(trace_text, "picmip_world=0->1"));
	assert(strstr(trace_text, "texture_precache=2->1"));
	assert(strstr(trace_text, "sound_precache=1->0"));
	assert(strstr(trace_text, "sound_streaming=0->1"));
	assert(strstr(trace_text, "retail64_ceiling_violations=6"));
	assert(strstr(trace_text, "enhanced_material_layers=0"));
	assert(strstr(trace_text, "reduced_color_textures=1"));

	reset(128, 82);
	assert(Xbox_MemoryProfileInitialize(path));
	assert(Xbox_MemoryProfilePolicy()->profile == XBOX_MEMORY_PROFILE_DEV128);
	assert(Xbox_MemoryProfileAllowsEnhancedMaterialLayers());
	assert(!Xbox_MemoryProfileUsesReducedColorTextures());
	Xbox_MemoryProfileRegisterCommands();
	registered_command();
	assert(cvars[0].integer == 2048);
	assert(cvars[1].integer == 0);
	assert(cvars[2].integer == 0);
	assert(cvars[3].integer == 2);
	assert(cvars[4].integer == 1);
	assert(cvars[5].integer == 0);
	assert(strstr(trace_text, "diagnostic-only"));
	assert(strstr(trace_text, "gl_max_size=2048->2048"));
	assert(strstr(trace_text, "retail64_ceiling_violations=6"));
	assert(strstr(trace_text, "enhanced_material_layers=1"));
	assert(strstr(trace_text, "reduced_color_textures=0"));

	remove(path);
	reset(64, 18);
	assert(Xbox_MemoryProfileInitialize(path));
	Xbox_MemoryProfileRegisterCommands();
	query_fail_on_call = 2;
	registered_command();
	assert(strstr(trace_text, "available=unavailable"));

	reset(64, 18);
	assert(Xbox_MemoryProfileInitialize(path));
	query_available_bytes = 7 * MIB + 5 * PAGE_SIZE;
	Xbox_MemoryTraceLoadFailure("gfx/menu/background.tga", 8388652, 4096);
	assert(strstr(trace_text,
		"load failure path=gfx/menu/background.tga expected=8388652 "
		"actual=4096 available_pages=1797 available=7 MiB"));

	write_token(path, "xemu64\n");
	reset(128, 80);
	assert(Xbox_MemoryProfileInitialize(path));
	assert(Xbox_MemoryProfilePolicy()->profile == XBOX_MEMORY_PROFILE_XEMU64);
	assert(!Xbox_MemoryProfileAllowsEnhancedMaterialLayers());
	assert(Xbox_MemoryProfileUsesReducedColorTextures());
	assert(strstr(trace_text, "request=xemu64"));
	Xbox_MemoryProfileRegisterCommands();
	registered_command();
	assert(cvars[1].integer == 2);

	write_token(path, "dev128");
	reset(64, 18);
	assert(Xbox_MemoryProfileInitialize(path));
	assert(Xbox_MemoryProfilePolicy()->profile == XBOX_MEMORY_PROFILE_RETAIL64);
	assert(strstr(trace_text, "dev128 unavailable"));

	write_token(path, "invalid");
	reset(128, 80);
	assert(Xbox_MemoryProfileInitialize(path));
	assert(Xbox_MemoryProfilePolicy()->profile == XBOX_MEMORY_PROFILE_DEV128);
	assert(strstr(trace_text, "invalid override"));

	write_token(path, "retail64 with trailing garbage that is too long");
	reset(128, 80);
	assert(Xbox_MemoryProfileInitialize(path));
	assert(Xbox_MemoryProfilePolicy()->profile == XBOX_MEMORY_PROFILE_DEV128);
	assert(strstr(trace_text, "invalid override"));

	remove(path);
	return 0;
}
