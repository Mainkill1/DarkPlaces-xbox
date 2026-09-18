#ifndef TEST_QUAKEDEF_H
#define TEST_QUAKEDEF_H

typedef int qboolean;

#define true 1
#define false 0
#define strcpy DO_NOT_USE_STRCPY__USE_STRLCPY_OR_MEMCPY

typedef struct cvar_s
{
	int flags;
	char *name;
	char *string;
	char *description;
	int integer;
	float value;
} cvar_t;

cvar_t *Cvar_FindVar(const char *name);
void Cvar_SetValueQuick(cvar_t *var, float value);
void Cmd_AddCommand(const char *name, void (*function)(void), const char *description);

#endif
