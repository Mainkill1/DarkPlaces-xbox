/* SPDX-License-Identifier: GPL-2.0-or-later
 * Engine integration for the offline, controller-operated attract profile.
 * The portable policy owns no engine pointers and never queues commands.
 */
#include "quakedef.h"
#include "cl_attract.h"
#include "cl_graphics_menu.h"
#include "xbox/attract_policy.h"

static dp_attract_t attract;
static dp_button_gate_t button_gate;
static char playlist[DP_ATTRACT_MAX_DEMOS][DP_ATTRACT_MAX_PATH];
static unsigned playlist_count;
static double signon_deadline;
static qbool escape_consumed;
static qbool error_menu_pending;
static int previous_destination = -1;
static unsigned previous_menu_context;
static cvar_t xbox_demo_loadtimeout = {CF_CLIENT, "xbox_demo_loadtimeout", "60", "seconds allowed for demo signon; failures stop the loop rather than retry indefinitely"};

qbool CL_Attract_Enabled(void)
{
    if (cls.state == ca_dedicated) return false;
#ifdef DP_PLATFORM_XBOX
    return true;
#else
    return Sys_CheckParm("-xboxbenchmark") != 0;
#endif
}
static void CL_Attract_Menu(void)
{
    if (CL_Attract_Enabled()) { CL_GraphicsMenu_Open(); return; }
#ifdef CONFIG_MENU
    if (MR_ToggleMenu) MR_ToggleMenu(1);
    else
#endif
        key_consoleactive |= KEY_CONSOLEACTIVE_USER;
}
void CL_Attract_Error(const char *reason)
{
    if (!CL_Attract_Enabled()) return;
    DP_Attract_Fail(&attract);
    error_menu_pending = true;
    cls.demonum = -1;
    Con_Printf(CON_ERROR "XBOX_AUTOPLAY_FAILED: %s\n", reason);
}
static void CL_Attract_Stop(void)
{
    error_menu_pending = false;
    DP_Attract_Stop(&attract); /* cancel next-demo work BEFORE disconnect */
    cls.demonum = -1;
    CL_Disconnect();
    DP_ButtonGate_Reset(&button_gate);
    Key_ReleaseAll();
    CL_Attract_Menu();
    Con_Print("XBOX_AUTOPLAY_INTERRUPTED: Start in the menu restarts the playlist\n");
}
static void CL_Attract_Playlist_f(cmd_state_t *cmd)
{
    unsigned i, count = (unsigned)(Cmd_Argc(cmd) - 1);
    if (!CL_Attract_Enabled()) return;
    if (DP_Attract_Active(&attract)) CL_Attract_Stop();
    playlist_count = 0;
    if (!count || count > DP_ATTRACT_MAX_DEMOS) {
        CL_Attract_Error("playlist requires 1 to 8 explicit .dem paths");
        return;
    }
    for (i = 0; i < count; ++i) {
        const char *path = Cmd_Argv(cmd, (int)i + 1);
        if (!DP_DemoPathValid(path)) { CL_Attract_Error("invalid demo path"); return; }
        dp_strlcpy(playlist[i], path, sizeof(playlist[i]));
    }
    playlist_count = count;
}
static void CL_Attract_Start_f(cmd_state_t *cmd)
{
    unsigned i;
    (void)cmd;
    if (!CL_Attract_Enabled()) {
        Con_Print("Use -xboxbenchmark for the desktop attract profile; Xbox enables it by default.\n");
        return;
    }
    if (!playlist_count) { CL_Attract_Error("no playlist in xbox-benchmark.cfg"); CL_Attract_Menu(); return; }
    /* Do not discard a healthy run before an explicit restart has been validated. */
    for (i = 0; i < playlist_count; ++i) {
        qfile_t *file = FS_OpenVirtualFile(playlist[i], false);
        char header[16];
        int track;
        size_t consumed;
        fs_offset_t size;
        if (!file) { CL_Attract_Error(playlist[i]); CL_Disconnect(); CL_Attract_Menu(); return; }
        size = FS_Read(file, header, sizeof(header));
        FS_Close(file);
        if (size <= 0 || !DP_DemoTrackHeader(header, (size_t)size, &track, &consumed)) {
            CL_Attract_Error("missing or malformed demo header"); CL_Disconnect(); CL_Attract_Menu(); return;
        }
    }
    CL_GraphicsMenu_Close();
    error_menu_pending = false;
    DP_Attract_Start(&attract, playlist_count);
    cls.demonum = -1;
    CL_Disconnect();
    DP_ButtonGate_Reset(&button_gate);
    Key_ReleaseAll();
    key_consoleactive = 0;
#ifdef CONFIG_MENU
    if (MR_ToggleMenu) MR_ToggleMenu(0);
#endif
    key_dest = key_game;
    Con_Print("XBOX_AUTOPLAY_START: input-free playlist; press a controller button to leave\n");
}
static void CL_Attract_Stop_f(cmd_state_t *cmd)
{
    (void)cmd;
    if (CL_Attract_Enabled()) CL_Attract_Stop();
}
static void CL_Attract_Status_f(cmd_state_t *cmd)
{
    (void)cmd;
    Con_Printf("XBOX_AUTOPLAY state=%d demo=%u/%u loops=%" PRIu64 "\n",
               (int)attract.state, attract.index, attract.count, attract.loops);
}
void CL_Attract_Init(void)
{
    DP_Attract_Init(&attract);
    CL_GraphicsMenu_Init();
    previous_menu_context = 0;
    DP_ButtonGate_Reset(&button_gate);
    playlist_count = 0;
    previous_destination = -1;
    escape_consumed = false;
    error_menu_pending = false;
    Cvar_RegisterVariable(&xbox_demo_loadtimeout);
    Cmd_AddCommand(CF_CLIENT, "xbox_demo_playlist", CL_Attract_Playlist_f, "set 1-8 explicit demo paths for the offline attract profile");
    Cmd_AddCommand(CF_CLIENT, "xbox_demo_start", CL_Attract_Start_f, "restart the attract playlist from its first demo");
    Cmd_AddCommand(CF_CLIENT, "xbox_demo_stop", CL_Attract_Stop_f, "cancel autoplay and open the menu");
    Cmd_AddCommand(CF_CLIENT, "xbox_demo_status", CL_Attract_Status_f, "report attract state, playlist index and completed loops");
}
void CL_Attract_Boot(void)
{
    if (!CL_Attract_Enabled()) return;
    Cvar_SetValueQuick(&joy_enable, 1);
    Cvar_SetValueQuick(&cl_startdemos, 0);
    cls.demonum = -1;
    if (Sys_CheckParm("-demo") || Sys_CheckParm("-benchmark") || Sys_CheckParm("-capturedemo") || Sys_CheckParm("-listen")) {
        CL_Attract_Error("do not combine the attract profile with one-shot demo or listen options");
        return;
    }
    /* Runs on the first normal Host_Frame, after FS, commands, video and menu
     * startup. Corrupt content then reaches Host_Error's recoverable path. */
    Cbuf_AddText(cmd_local, "exec xbox-benchmark.cfg\n");
    CL_GraphicsMenu_BootConfig();
    Cbuf_AddText(cmd_local, "xbox_demo_start\n");
}
void CL_Attract_Frame(void)
{
    unsigned index;
    if (!CL_Attract_Enabled()) return;
    if (error_menu_pending && !cls.demoplayback) {
        error_menu_pending = false;
        CL_Attract_Menu();
    }
    if (DP_Attract_TakeNext(&attract, &index)) {
        cls.demonum = -1;
        CL_GraphicsMenu_LogSettings();
        CL_PlayDemo(playlist[index]);
        DP_Attract_Loaded(&attract, cls.demoplayback);
        if (!cls.demoplayback) { CL_Attract_Error("demo could not start"); CL_Attract_Menu(); return; }
        signon_deadline = host.realtime + bound(1, xbox_demo_loadtimeout.value, 600);
        Con_Printf("XBOX_AUTOPLAY_DEMO index=%u loops=%" PRIu64 " path=%s\n", index, attract.loops, playlist[index]);
    }
    if (attract.state == DP_ATTRACT_PLAYING && cls.signon != SIGNONS && host.realtime >= signon_deadline) {
        CL_Attract_Error("demo signon timed out; check map, CSQC and other content dependencies");
        CL_Disconnect();
        CL_Attract_Menu();
    }
}
qbool CL_Attract_DemoEnded(void)
{
    qbool valid;
    if (!CL_Attract_Enabled() || attract.state != DP_ATTRACT_PLAYING) return false;
    valid = cls.signon == SIGNONS;
    DP_Attract_Ended(&attract, valid);
    if (!valid) {
        CL_Attract_Error("demo ended before completing signon");
        CL_Attract_Menu();
    }
    return true;
}
void CL_Attract_Disconnect(void)
{
    if (CL_Attract_Enabled() && attract.state == DP_ATTRACT_PLAYING && !cls.demostarting)
        DP_Attract_Stop(&attract); /* manual connect/map/disconnect is not demo EOF */
}
qbool CL_Attract_KeyEvent(int key, qbool down)
{
    if (!CL_Attract_Enabled() || key != K_ESCAPE) return false;
    if (escape_consumed) { if (!down) escape_consumed = false; return true; }
    if (down && DP_Attract_Active(&attract)) {
        CL_Attract_Stop();
        escape_consumed = true;
        return true;
    }
    return false;
}
void CL_Attract_Controller(const dp_pad_sample_t *s, vid_joystate_t *out)
{
    uint32_t pressed;
    unsigned i;
    int destination = key_consoleactive ? key_console : key_dest;
    memset(out, 0, sizeof(*out));
    out->is360 = true; /* stable logical mapping even for a disconnected device */
    if (previous_destination != destination || previous_menu_context != CL_GraphicsMenu_Context()) {
        previous_menu_context = CL_GraphicsMenu_Context();
        previous_destination = destination;
        DP_ButtonGate_Reset(&button_gate);
        Key_ReleaseAll();
        memset(&vid_joystate, 0, sizeof(vid_joystate));
        vid_joystate.is360 = true;
    }
    pressed = DP_ButtonGate_Update(&button_gate, s->connected != 0, s->instance, s->buttons);
    if (DP_Attract_Active(&attract)) {
        if (pressed) CL_Attract_Stop();
        return; /* sticks and all normal actions are isolated from recorded playback */
    }
    if (destination == key_menu && (pressed & (1u << DP_PAD_Y))) {
        CL_GraphicsMenu_Open();
        DP_ButtonGate_Reset(&button_gate);
        return;
    }
    if ((pressed & (1u << DP_PAD_START)) && !CL_GraphicsMenu_Editing()) {
        if (destination == key_menu && (attract.state == DP_ATTRACT_MANUAL || attract.state == DP_ATTRACT_FAILED)) {
            CL_Attract_Start_f(cmd_local);
            return;
        }
    }
    if (!button_gate.armed || !s->connected) return;
    for (i = 0; i < 16; ++i) out->button[i] = (s->buttons & (1u << i)) != 0;
    /* Menu navigation uses deliberate stick deflection, never the takeover gate. */
    if (destination != key_game) {
        out->button[16] = s->axis[1] < -0.55f;
        out->button[17] = s->axis[1] >  0.55f;
        out->button[18] = s->axis[0] < -0.55f;
        out->button[19] = s->axis[0] >  0.55f;
    } else {
        for (i = 0; i < 6; ++i) out->axis[i] = s->axis[i];
    }
}
