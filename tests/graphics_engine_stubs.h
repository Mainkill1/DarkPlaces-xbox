/* Service doubles only; production menu implementation is compiled unchanged. */
#ifndef DP_GRAPHICS_TEST_STUBS
#define DP_GRAPHICS_TEST_STUBS
#define FS_Close AttractTest_CloseUnused
#include "autoplay_engine_stubs.h"
#undef FS_Close
int FS_Close(qfile_t *);
#define CF_ARCHIVE 2
#define CF_READONLY 4
#define MAX_KEYS 512
#define K_ENTER 13
#define K_UPARROW 128
#define K_DOWNARROW 129
#define K_LEFTARROW 130
#define K_RIGHTARROW 131
#define max(a,b) ((a)>(b)?(a):(b))
#define min(a,b) ((a)<(b)?(a):(b))
#define FONT_DEFAULT NULL
#define dpsnprintf snprintf
typedef struct { int unused; } cvar_state_t;
extern cvar_state_t cvars_all;
extern struct test_vid { struct { int ext_texture_filter_anisotropic; } support; int max_anisotropy; } vid;
extern cvar_t vid_conwidth, vid_conheight;
float Cvar_VariableValue(cvar_state_t *, const char *, unsigned);
cvar_t *Cvar_FindVar(cvar_state_t *, const char *, unsigned);
void Cvar_SetValue(cvar_state_t *, const char *, float);
const char *FS_FileExists(const char *);
qfile_t *FS_OpenRealFile(const char *, const char *, qbool);
fs_offset_t FS_Write(qfile_t *, const void *, size_t);
void FS_RemoveOnClose(qfile_t *);
void DrawQ_Fill(float,float,float,float,float,float,float,float,int);
float DrawQ_String(float,float,const char *,size_t,float,float,float,float,float,float,int,int *,qbool,const void *);
#endif
