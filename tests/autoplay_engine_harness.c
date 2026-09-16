#include <assert.h>
#include "autoplay_engine_stubs.h"
#include "cl_attract.h"
#include "cl_graphics_menu.h"

struct test_cls cls;
struct test_host host;
int key_dest, key_consoleactive;
vid_joystate_t vid_joystate;
cvar_t joy_enable, cl_startdemos;
static cmd_state_t command;
cmd_state_t *cmd_local = &command;
static qbool menu_editing;
static unsigned menu_context;
void CL_GraphicsMenu_Init(void) { menu_editing=false; menu_context=0; }
void CL_GraphicsMenu_BootConfig(void) { }
void CL_GraphicsMenu_Open(void) { key_dest=key_menu; ++menu_context; menu_editing=false; }
void CL_GraphicsMenu_Close(void) { ++menu_context; menu_editing=false; }
qbool CL_GraphicsMenu_Editing(void) { return menu_editing; }
unsigned CL_GraphicsMenu_Context(void) { return menu_context; }
void CL_GraphicsMenu_LogSettings(void) { }
static void menu(int open) { key_dest = open ? key_menu : key_game; }
void (*MR_ToggleMenu)(int) = menu;
static int enabled = 1, file_missing, load_failure, plays, disconnects, errors;
static int argc;
static const char *argv[10];
static char queue[1024], last_demo[128];
static struct { const char *name; void (*call)(cmd_state_t *); } commands[4];
static unsigned command_count;
int Sys_CheckParm(const char *arg) { return enabled && !strcmp(arg, "-xboxbenchmark"); }
void Con_Print(const char *text) { (void)text; }
void Con_Printf(const char *format, ...) { if (strstr(format, "FAILED")) ++errors; }
void Cvar_RegisterVariable(cvar_t *v) { v->value = (float)atof(v->string); v->integer = atoi(v->string); }
void Cvar_SetValueQuick(cvar_t *v, float value) { v->value = value; v->integer = (int)value; }
void Cmd_AddCommand(int f, const char *n, void (*c)(cmd_state_t *), const char *d)
{ (void)f; (void)d; assert(command_count < 4); commands[command_count].name=n; commands[command_count++].call=c; }
int Cmd_Argc(cmd_state_t *c) { (void)c; return argc; }
const char *Cmd_Argv(cmd_state_t *c, int i) { (void)c; return argv[i]; }
size_t dp_strlcpy(char *d, const char *s, size_t size) { size_t n=strlen(s); assert(n<size); memcpy(d,s,n+1); return n; }
qfile_t *FS_OpenVirtualFile(const char *n, qbool q)
{ static qfile_t file; (void)n; (void)q; file.offset=0; return file_missing ? NULL : &file; }
fs_offset_t FS_Read(qfile_t *f, void *out, size_t size) { (void)f; assert(size>=3); memcpy(out,"-1\n",3); return 3; }
void FS_Close(qfile_t *f) { (void)f; }
void CL_Disconnect(void) { CL_Attract_Disconnect(); ++disconnects; cls.demoplayback=false; cls.signon=0; }
void CL_PlayDemo(const char *name) { ++plays; strcpy(last_demo,name); cls.demoplayback=!load_failure; cls.signon=0; }
void Key_ReleaseAll(void) { }
void Cbuf_AddText(cmd_state_t *c, const char *t) { (void)c; assert(strlen(queue)+strlen(t)<sizeof(queue)); strcat(queue,t); }
static void run_command(const char *name)
{ unsigned i; for(i=0;i<command_count;i++) if(!strcmp(name,commands[i].name)) { commands[i].call(cmd_local); return; } assert(0); }
static void sample(dp_pad_sample_t *s, vid_joystate_t *out) { CL_Attract_Controller(s,out); vid_joystate=*out; }
int main(void)
{
    dp_pad_sample_t pad = {0};
    vid_joystate_t out;
    int old;
    CL_Attract_Init();
    enabled=0;
    CL_Attract_Boot();
    assert(!*queue && !plays); /* ordinary desktop startup remains unchanged */
    enabled=1;
    CL_Attract_Boot();
    assert(!strcmp(queue,"exec xbox-benchmark.cfg\nxbox_demo_start\n"));
    argc=3; argv[1]="demos/a.dem"; argv[2]="demos/b.dem";
    run_command("xbox_demo_playlist"); run_command("xbox_demo_start");
    assert(!plays);
    CL_Attract_Frame(); assert(plays==1 && !strcmp(last_demo,"demos/a.dem"));
    cls.signon=SIGNONS;
    assert(CL_Attract_DemoEnded()); CL_Disconnect(); CL_Attract_Frame();
    assert(plays==2 && !strcmp(last_demo,"demos/b.dem"));
    cls.signon=SIGNONS;
    assert(CL_Attract_DemoEnded()); CL_Disconnect(); CL_Attract_Frame();
    assert(plays==3 && !strcmp(last_demo,"demos/a.dem"));
    /* No controller or stick movement can terminate a demo. */
    sample(&pad,&out); assert(cls.demoplayback);
    pad.connected=1; pad.instance=22; pad.axis[0]=0.9f;
    sample(&pad,&out); assert(cls.demoplayback && out.axis[0]==0);
    pad.buttons=1u<<DP_PAD_A;
    sample(&pad,&out); assert(!cls.demoplayback && key_dest==key_menu && !out.button[DP_PAD_A]);
    CL_Attract_Frame(); assert(plays==3);
    sample(&pad,&out); assert(!out.button[DP_PAD_A]); /* held takeover does not confirm */
    pad.buttons=0; sample(&pad,&out);
    pad.buttons=1u<<DP_PAD_A; sample(&pad,&out); assert(out.button[DP_PAD_A]);
    pad.buttons=0; sample(&pad,&out);
    menu_editing=true; ++menu_context; /* actual menu's page-change contract */
    sample(&pad,&out);
    pad.buttons=1u<<DP_PAD_START; sample(&pad,&out);
    assert(out.button[DP_PAD_START] && !cls.demoplayback); /* Start goes Back, not play */
    pad.buttons=0; sample(&pad,&out);
    menu_editing=false; ++menu_context; sample(&pad,&out);
    pad.buttons=1u<<DP_PAD_START; sample(&pad,&out); assert(!out.button[DP_PAD_START]);
    CL_Attract_Frame(); assert(plays==4 && !strcmp(last_demo,"demos/a.dem"));
    /* Error is latched, never retried in a tight loop. */
    CL_Attract_Error("test error"); CL_Disconnect(); old=plays;
    key_dest=key_game;
    CL_Attract_Frame(); CL_Attract_Frame(); assert(plays==old && key_dest==key_menu);
    run_command("xbox_demo_start"); CL_Attract_Frame();
    host.realtime=61; CL_Attract_Frame(); assert(!cls.demoplayback && key_dest==key_menu);
    old=plays; CL_Attract_Frame(); assert(plays==old);
    /* Missing file preflight blocks a restart before playback begins. */
    file_missing=1; run_command("xbox_demo_start"); CL_Attract_Frame(); assert(plays==old);
    file_missing=0; run_command("xbox_demo_start"); CL_Attract_Frame();
    assert(CL_Attract_KeyEvent(K_ESCAPE,true)); assert(!cls.demoplayback);
    assert(CL_Attract_KeyEvent(K_ESCAPE,true)); assert(CL_Attract_KeyEvent(K_ESCAPE,false));
    old=plays; CL_Attract_Frame(); assert(plays==old);
    /* A demo ending before signon is a failure, not an empty-file spin. */
    run_command("xbox_demo_start"); CL_Attract_Frame(); assert(CL_Attract_DemoEnded()); CL_Disconnect();
    old=plays; CL_Attract_Frame(); assert(plays==old && errors>=3);
    assert(disconnects>0);
    return 0;
}
