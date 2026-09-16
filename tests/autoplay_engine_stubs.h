/* Test boundary only: real cl_attract.c linked against deterministic engine services. */
#ifndef DP_AUTOPLAY_ENGINE_STUBS_H
#define DP_AUTOPLAY_ENGINE_STUBS_H
#define QUAKEDEF_H
#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include "qtypes.h"
#define CF_CLIENT 1
#define CON_ERROR ""
#define SIGNONS 4
#define KEY_CONSOLEACTIVE_USER 1
#define K_ESCAPE 27
#define bound(a,b,c) ((b)<(a)?(a):((b)>(c)?(c):(b)))
enum { ca_disconnected, ca_connected, ca_dedicated };
enum { key_game, key_menu, key_console };
typedef struct { int unused; } cmd_state_t;
typedef struct { int flags; const char *name, *string, *description; int integer; float value; } cvar_t;
typedef struct vid_joystate_s { float axis[16]; unsigned char button[36]; qbool is360; } vid_joystate_t;
typedef long long fs_offset_t;
typedef struct { size_t offset; } qfile_t;
extern struct test_cls { int state, demonum; qbool demoplayback, demostarting; int signon; } cls;
extern struct test_host { double realtime; } host;
extern int key_dest, key_consoleactive;
extern vid_joystate_t vid_joystate;
extern cvar_t joy_enable, cl_startdemos;
extern cmd_state_t *cmd_local;
extern void (*MR_ToggleMenu)(int);
int Sys_CheckParm(const char *arg);
void Con_Print(const char *message);
void Con_Printf(const char *format, ...);
void Cvar_RegisterVariable(cvar_t *var);
void Cvar_SetValueQuick(cvar_t *var, float value);
void Cmd_AddCommand(int flags, const char *name, void (*callback)(cmd_state_t *), const char *description);
int Cmd_Argc(cmd_state_t *cmd);
const char *Cmd_Argv(cmd_state_t *cmd, int index);
size_t dp_strlcpy(char *dest, const char *source, size_t size);
qfile_t *FS_OpenVirtualFile(const char *name, qbool quiet);
fs_offset_t FS_Read(qfile_t *file, void *output, size_t size);
void FS_Close(qfile_t *file);
void CL_Disconnect(void);
void CL_PlayDemo(const char *name);
void Key_ReleaseAll(void);
void Cbuf_AddText(cmd_state_t *cmd, const char *text);
#endif
