#include <assert.h>
#include <math.h>
#include "graphics_engine_stubs.h"
#include "cl_graphics_menu.h"

int key_dest = key_game, key_consoleactive;
cvar_state_t cvars_all;
struct test_vid vid;
cvar_t vid_conwidth = {.value=640}, vid_conheight = {.value=480};
static cmd_state_t cmd;
cmd_state_t *cmd_local = &cmd;
static int enabled=1, save_success=1, short_write, close_failure, remove_called, saved_exists, game_menu_calls;
static char queue[8192], saved[4096], drawn[8192];
static cvar_t vars[64];
static unsigned count;
static void game_menu(int mode) { assert(mode==1); ++game_menu_calls; key_dest=key_menu; }
void (*MR_ToggleMenu)(int)=game_menu;
qbool CL_Attract_Enabled(void) { return enabled; }
void Key_ReleaseAll(void) { }
void Con_Printf(const char *format, ...) { (void)format; }
void Cbuf_AddText(cmd_state_t *c, const char *s) { (void)c; assert(strlen(queue)+strlen(s)<sizeof(queue)); strcat(queue,s); }
size_t dp_strlcpy(char *d, const char *s, size_t n) { size_t len=strlen(s); assert(len<n); memcpy(d,s,len+1); return len; }
cvar_t *Cvar_FindVar(cvar_state_t *state,const char *name,unsigned flags)
{ unsigned i; (void)state; (void)flags; for(i=0;i<count;i++) if(!strcmp(name,vars[i].name)) return &vars[i]; return NULL; }
float Cvar_VariableValue(cvar_state_t *state,const char *name,unsigned flags)
{ cvar_t *v=Cvar_FindVar(state,name,flags); return v?v->value:0; }
void Cvar_SetValue(cvar_state_t *state,const char *name,float value)
{ cvar_t *v=Cvar_FindVar(state,name,CF_CLIENT); assert(v); assert(!(v->flags&CF_READONLY)); v->value=value; }
static void add(const char *name,float value) { assert(count<64); vars[count].name=name; vars[count].value=value; vars[count++].flags=CF_CLIENT; }
void Cvar_RegisterVariable(cvar_t *v) { add(v->name,(float)atof(v->string)); }
const char *FS_FileExists(const char *p) { assert(!strcmp(p,"xbox-graphics.cfg")); return saved_exists?p:NULL; }
qfile_t *FS_OpenRealFile(const char *name,const char *mode,qbool quiet)
{ static qfile_t file; (void)quiet; assert(!strcmp(name,"xbox-graphics.cfg") && !strcmp(mode,"wb")); return save_success?&file:NULL; }
fs_offset_t FS_Write(qfile_t *file,const void *data,size_t len)
{ (void)file; assert(len>0 && len<sizeof(saved)); memcpy(saved,data,len); saved[len]=0; return short_write?(fs_offset_t)len-1:(fs_offset_t)len; }
int FS_Close(qfile_t *file) { (void)file; return close_failure?-1:0; }
void FS_RemoveOnClose(qfile_t *file) { (void)file; ++remove_called; }
void DrawQ_Fill(float x,float y,float w,float h,float r,float g,float b,float a,int flags)
{ (void)x;(void)y;(void)w;(void)h;(void)r;(void)g;(void)b;(void)a;(void)flags; }
float DrawQ_String(float x,float y,const char *s,size_t len,float sx,float sy,float r,float g,float b,float a,int flags,int *out,qbool ignore,const void *font)
{ (void)x;(void)y;(void)len;(void)sx;(void)sy;(void)r;(void)g;(void)b;(void)a;(void)flags;(void)out;(void)ignore;(void)font; assert(strlen(drawn)+strlen(s)+2<sizeof(drawn)); strcat(drawn,s); strcat(drawn,"\n"); return 0; }
static void press(int key) { assert(CL_GraphicsMenu_KeyEvent(key,true)); assert(CL_GraphicsMenu_KeyEvent(key,false)); }
static void down(unsigned n) { while(n--) press(K_DOWNARROW); }
static void draw(void) { drawn[0]=0; assert(CL_GraphicsMenu_Draw()); }
static float get(const char *name) { return Cvar_VariableValue(&cvars_all,name,CF_CLIENT); }
int main(void)
{
    unsigned i, oldcontext;
    const char *names[]={"cl_minfps","cl_maxfps","vid_vsync","gl_picmip","gl_texture_anisotropy","cl_particles","cl_particles_quality","cl_decals","r_coronas","gl_flashblend","r_shadow_realtime_dlight","r_shadow_realtime_dlight_shadows","r_shadow_realtime_world","r_shadow_realtime_world_shadows","r_bloom","r_water","r_sky","v_gamma","cl_minfps_force","cl_minfps_qualitymin","cl_minfps_qualitymax"};
    for(i=0;i<sizeof(names)/sizeof(names[0]);++i) add(names[i],0);
    Cvar_SetValue(&cvars_all,"cl_particles_quality",2);
    CL_GraphicsMenu_Init();
    enabled=0; CL_GraphicsMenu_Open(); assert(!CL_GraphicsMenu_Draw());
    enabled=1;
    Cvar_SetValue(&cvars_all,"cl_minfps",40);
    CL_GraphicsMenu_BootConfig(); assert(!queue[0] && get("cl_minfps")==0);
    saved_exists=1; CL_GraphicsMenu_BootConfig(); assert(!strcmp(queue,"exec xbox-graphics.cfg\n")); queue[0]=0;
    CL_GraphicsMenu_Open(); oldcontext=CL_GraphicsMenu_Context();
    assert(key_dest==key_menu && !CL_GraphicsMenu_Editing()); draw(); assert(strstr(drawn,"Graphics settings"));
    press(K_ENTER); assert(CL_GraphicsMenu_Editing() && CL_GraphicsMenu_Context()!=oldcontext);
    draw(); assert(strstr(drawn,"Automatic quality: OFF"));
    assert(CL_GraphicsMenu_KeyEvent(K_ENTER,true)); assert(get("cl_minfps")==60);
    assert(get("cl_minfps_qualitymin")==0.25f && get("cl_minfps_qualitymax")==1 && get("cl_minfps_force")==0);
    assert(CL_GraphicsMenu_KeyEvent(K_ENTER,true)); assert(get("cl_minfps")==60); /* repeats do not flip */
    assert(CL_GraphicsMenu_KeyEvent(K_ENTER,false));
    press(K_LEFTARROW); assert(get("cl_minfps")==0 && get("cl_particles_quality")==2);
    press(K_DOWNARROW); press(K_LEFTARROW); assert(get("xbox_autoquality_target")==50 && get("cl_minfps")==0);
    press(K_UPARROW); press(K_RIGHTARROW); assert(get("cl_minfps")==50);
    press(K_DOWNARROW); press(K_LEFTARROW); assert(get("cl_minfps")==40);
    press(K_DOWNARROW); press(K_RIGHTARROW); assert(get("cl_maxfps")==30 && get("cl_minfps")==40);
    /* Independent VSync and delayed texture reload. */
    press(K_DOWNARROW); press(K_ENTER); assert(get("vid_vsync")==1);
    press(K_DOWNARROW); press(K_RIGHTARROW); assert(get("gl_picmip")==1 && !strstr(queue,"r_restart"));
    press(K_DOWNARROW); press(K_RIGHTARROW); assert(get("gl_texture_anisotropy")==1);
    vid.support.ext_texture_filter_anisotropic=1; vid.max_anisotropy=4;
    press(K_RIGHTARROW); press(K_RIGHTARROW); press(K_RIGHTARROW); assert(get("gl_texture_anisotropy")==4);
    press(K_DOWNARROW); Cvar_FindVar(&cvars_all,"cl_particles",CF_CLIENT)->flags |= CF_READONLY;
    press(K_ENTER); assert(get("cl_particles")==0); draw(); assert(strstr(drawn,"Unavailable"));
    /* Scroll all three pages into reload/save rows; actual draw strings checked. */
    down(13); draw(); assert(strstr(drawn,"Apply texture changes"));
    press(K_ENTER); assert(!strcmp(queue,"r_restart\n")); queue[0]=0;
    press(K_ENTER); assert(!queue[0]);
    press(K_DOWNARROW); press(K_ENTER); assert(strstr(saved,"cl_minfps 40\n") && strstr(saved,"gl_picmip 1\n"));
    assert(!strstr(saved,"cl_particles ")); draw(); assert(strstr(drawn,"Saved."));
    save_success=0; press(K_ENTER); draw(); assert(strstr(drawn,"session-only"));
    save_success=1; short_write=1; press(K_ENTER); draw(); assert(strstr(drawn,"session-only") && remove_called==1);
    short_write=0; close_failure=1; press(K_ENTER); draw(); assert(strstr(drawn,"session-only"));
    close_failure=0;
    /* A changed preference is not reset on opening, closing or restarting. */
    press(K_ESCAPE); assert(!CL_GraphicsMenu_Editing());
    press(K_DOWNARROW); press(K_ENTER); assert(!CL_GraphicsMenu_Draw());
    assert(!strcmp(queue,"xbox_demo_start\n") && get("cl_minfps")==40);
    CL_GraphicsMenu_Open(); press(K_ESCAPE); assert(game_menu_calls==1);
    assert(!CL_GraphicsMenu_KeyEvent(K_ENTER,true));
    CL_GraphicsMenu_LogSettings();
    return 0;
}
