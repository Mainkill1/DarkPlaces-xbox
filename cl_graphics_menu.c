/* SPDX-License-Identifier: GPL-2.0-or-later
 * Engine-owned controller menu: it does not depend on a particular menu.dat.
 * All edits use existing cvars; this is not a second graphics renderer.
 */
#include "quakedef.h"
#include "cl_attract.h"
#include "cl_graphics_menu.h"

#define GRAPHICS_PAGE_ROWS 8
#define GRAPHICS_CONFIG "xbox-graphics.cfg"

typedef enum { GM_CLOSED, GM_HOME, GM_SETTINGS } graphics_page_t;
typedef struct {
    const char *label, *name, *help;
    float choices[8];
    unsigned count;
} graphics_setting_t;

/* Ordering is the on-screen ordering. No arbitrary cvar/command text is saved. */
static const graphics_setting_t settings[] = {
    {"Automatic quality", "cl_minfps", "OFF keeps workload fixed. ON uses FPS-based quality.", {0,1}, 2},
    {"Auto quality target FPS", "xbox_autoquality_target", "Adaptation target only; this is NOT the frame cap.", {20,30,40,50,60,120}, 6},
    {"Frame cap (0 = unlimited)", "cl_maxfps", "Independent of the automatic quality target.", {0,30,60,120,240}, 5},
    {"VSync", "vid_vsync", "Presentation pacing; backend support is required.", {0,1}, 2},
    {"Texture reduction (powers of 2)", "gl_picmip", "Use Apply texture changes below to reload textures.", {0,1,2,3,4}, 5},
    {"Anisotropic filtering", "gl_texture_anisotropy", "Clamped to the active renderer's reported limit.", {1,2,4,8,16}, 5},
    {"Particles", "cl_particles", "Enable or disable particle effects.", {0,1}, 2},
    {"Particle amount multiplier", "cl_particles_quality", "Fixed particle count multiplier, not adaptive quality.", {0.25f,0.5f,1,2,4}, 5},
    {"Decals", "cl_decals", "Bullet marks, blood and other decals.", {0,1}, 2},
    {"Coronas", "r_coronas", "Light corona intensity: off or normal.", {0,1}, 2},
    {"Flashblend lights", "gl_flashblend", "Flashblend can replace real-time dynamic lighting.", {0,1}, 2},
    {"Real-time dynamic lights", "r_shadow_realtime_dlight", "Requires backend support; turn Flashblend off.", {0,1}, 2},
    {"Dynamic light shadows", "r_shadow_realtime_dlight_shadows", "Requires dynamic lighting and shadow support.", {0,1}, 2},
    {"Real-time world lighting", "r_shadow_realtime_world", "Requires backend support and suitable map lighting.", {0,1}, 2},
    {"World shadows", "r_shadow_realtime_world_shadows", "Requires real-time world lighting support.", {0,1}, 2},
    {"Bloom", "r_bloom", "Requires a backend implementing the bloom passes.", {0,1}, 2},
    {"Water reflections/refraction", "r_water", "Requires backend support and translucent water.", {0,1}, 2},
    {"Sky", "r_sky", "Enable or disable sky rendering.", {0,1}, 2},
    {"Gamma", "v_gamma", "Display correction; does not change scene workload.", {0.5f,0.75f,1,1.25f,1.5f,2}, 6}
};
#define GRAPHICS_SETTINGS ((unsigned)(sizeof(settings) / sizeof(settings[0])))
#define GRAPHICS_ROWS (GRAPHICS_SETTINGS + 3)
static cvar_t xbox_autoquality_target = {CF_CLIENT | CF_ARCHIVE, "xbox_autoquality_target", "60", "remembered automatic quality target when adaptation is disabled; not an FPS cap"};
static graphics_page_t page;
static unsigned cursor, context, revision;
static qbool texture_pending;
static unsigned char consumed[MAX_KEYS];
static char message[128];

static float Value(const char *name)
{
    return Cvar_VariableValue(&cvars_all, name, CF_CLIENT);
}
static qbool Available(const char *name)
{
    cvar_t *var = Cvar_FindVar(&cvars_all, name, CF_CLIENT);
    return var && !(var->flags & CF_READONLY);
}
static void Changed(const char *name, float value)
{
    float old = Value(name);
    Cvar_SetValue(&cvars_all, name, value);
    if (Value(name) == old) return;
    ++revision;
    Con_Printf("XBOX_GRAPHICS_CHANGE revision=%u name=%s value=%.9g\n", revision, name, (double)Value(name));
}
static void SetPage(graphics_page_t next)
{
    page = next;
    cursor = 0;
    ++context; /* tells input routing to require release across pages */
}
void CL_GraphicsMenu_Init(void)
{
    page = GM_CLOSED;
    cursor = context = revision = 0;
    texture_pending = false;
    memset(consumed, 0, sizeof(consumed));
    message[0] = 0;
    Cvar_RegisterVariable(&xbox_autoquality_target);
}
void CL_GraphicsMenu_BootConfig(void)
{
    /* Executed after the package's default-OFF config, before automatic start.
     * Deliberately saved user choices therefore win, not every-loop defaults. */
    Cvar_SetValue(&cvars_all, "cl_minfps", 0);
    Cvar_SetValue(&cvars_all, "cl_minfps_force", 0);
    if (FS_FileExists(GRAPHICS_CONFIG))
        Cbuf_AddText(cmd_local, "exec " GRAPHICS_CONFIG "\n");
}
void CL_GraphicsMenu_Open(void)
{
    if (!CL_Attract_Enabled()) return;
    Key_ReleaseAll();
    key_dest = key_menu;
    key_consoleactive = 0;
    SetPage(GM_HOME);
}
void CL_GraphicsMenu_Close(void)
{
    SetPage(GM_CLOSED);
}
qbool CL_GraphicsMenu_Editing(void)
{
    return page == GM_SETTINGS && key_dest == key_menu;
}
unsigned CL_GraphicsMenu_Context(void)
{
    return context;
}
static void GameMenu(void)
{
    CL_GraphicsMenu_Close();
#ifdef CONFIG_MENU
    if (MR_ToggleMenu) MR_ToggleMenu(1);
    else
#endif
        key_consoleactive |= KEY_CONSOLEACTIVE_USER;
}
static void Save(void)
{
    char buffer[4096];
    size_t used;
    unsigned i;
    int length;
    qfile_t *file;
    qbool success = false;
    length = dpsnprintf(buffer, sizeof(buffer), "// Controller graphics preferences; loaded after benchmark defaults.\n");
    if (length < 0) return;
    used = (size_t)length;
    for (i = 0; i < GRAPHICS_SETTINGS; ++i) {
        if (!Available(settings[i].name)) continue;
        length = dpsnprintf(buffer + used, sizeof(buffer) - used, "%s %.9g\n", settings[i].name, (double)Value(settings[i].name));
        if (length < 0 || (size_t)length >= sizeof(buffer) - used) {
            dp_strlcpy(message, "Save failed: preferences exceed buffer.", sizeof(message));
            return;
        }
        used += (size_t)length;
    }
    /* Store the adaptive interval too; never silently restore a 1..1 no-op. */
    length = dpsnprintf(buffer + used, sizeof(buffer) - used,
        "cl_minfps_force 0\ncl_minfps_qualitymin %.9g\ncl_minfps_qualitymax %.9g\n",
        (double)Value("cl_minfps_qualitymin"), (double)Value("cl_minfps_qualitymax"));
    if (length < 0 || (size_t)length >= sizeof(buffer) - used) return;
    used += (size_t)length;
    /* FS_WriteFile currently ignores short writes/close failures; check both. */
    file = FS_OpenRealFile(GRAPHICS_CONFIG, "wb", false);
    if (file) {
        qbool complete = FS_Write(file, buffer, used) == (fs_offset_t)used;
        int closed;
        if (!complete) FS_RemoveOnClose(file);
        closed = FS_Close(file);
        success = complete && closed == 0;
    }
    if (success)
        dp_strlcpy(message, "Saved. Preferences reload on the next launch.", sizeof(message));
    else
        dp_strlcpy(message, "Save FAILED. Changes are session-only (check storage).", sizeof(message));
    Con_Printf("XBOX_GRAPHICS_SAVE: %s\n", message);
}
static void Adjust(int direction, qbool activate)
{
    const graphics_setting_t *setting;
    float old, chosen;
    unsigned i;
    if (cursor == GRAPHICS_SETTINGS) {
        if (activate && texture_pending) {
            Cbuf_AddText(cmd_local, "r_restart\n");
            texture_pending = false;
            dp_strlcpy(message, "Renderer reload queued.", sizeof(message));
        }
        return;
    }
    if (cursor == GRAPHICS_SETTINGS + 1) { if (activate) Save(); return; }
    if (cursor == GRAPHICS_SETTINGS + 2) { if (activate) SetPage(GM_HOME); return; }
    setting = &settings[cursor];
    if (!Available(setting->name)) {
        dp_strlcpy(message, "Setting unavailable or read-only in this build.", sizeof(message));
        return;
    }
    old = Value(setting->name);
    if (cursor == 0) {
        if (old > 0) {
            Changed("xbox_autoquality_target", bound(1, old, 240));
            Changed("cl_minfps", 0);
        } else {
            /* A frozen quality interval would make the ON switch ineffective. */
            Changed("cl_minfps_qualitymin", 0.25f);
            Changed("cl_minfps_qualitymax", 1);
            Changed("cl_minfps_force", 0);
            Changed("cl_minfps", bound(1, Value("xbox_autoquality_target"), 240));
        }
        dp_strlcpy(message, Value("cl_minfps") > 0 ? "Adaptive quality ON: workload is not fixed." : "Adaptive quality OFF: manual graphics are unchanged.", sizeof(message));
        return;
    }
    chosen = old;
    if (direction > 0) {
        for (i = 0; i < setting->count; ++i)
            if (setting->choices[i] > old) { chosen = setting->choices[i]; break; }
        if (activate && chosen == old) chosen = setting->choices[0];
    } else {
        for (i = setting->count; i > 0; --i)
            if (setting->choices[i - 1] < old) { chosen = setting->choices[i - 1]; break; }
    }
    if (!strcmp(setting->name, "gl_texture_anisotropy")) {
        if (!vid.support.ext_texture_filter_anisotropic) chosen = 1;
        else chosen = bound(1, chosen, max(1, vid.max_anisotropy));
    }
    Changed(setting->name, chosen);
    if (cursor == 1 && Value("cl_minfps") > 0) Changed("cl_minfps", chosen);
    if (!strcmp(setting->name, "gl_picmip") && Value(setting->name) != old) texture_pending = true;
    dp_strlcpy(message, texture_pending ? "Texture change pending: use Apply texture changes." : "Changed for this session. Use Save to keep it.", sizeof(message));
}
qbool CL_GraphicsMenu_KeyEvent(int key, qbool down)
{
    qbool repeated;
    if (key < 0 || key >= MAX_KEYS) return false;
    if (!down && consumed[key]) { consumed[key] = 0; return true; }
    if (!CL_Attract_Enabled() || page == GM_CLOSED || key_consoleactive || key_dest != key_menu) return false;
    repeated = consumed[key] != 0;
    consumed[key] = down;
    if (!down) return true;
    if (key == K_ESCAPE) {
        if (!repeated) { if (page == GM_SETTINGS) SetPage(GM_HOME); else GameMenu(); }
    } else if (key == K_UPARROW || key == K_DOWNARROW) {
        unsigned count = page == GM_HOME ? 3 : GRAPHICS_ROWS;
        cursor = key == K_UPARROW ? (cursor + count - 1) % count : (cursor + 1) % count;
    } else if (key == K_LEFTARROW || key == K_RIGHTARROW || key == K_ENTER) {
        if (page == GM_HOME) {
            if (key != K_ENTER || repeated) return true;
            if (cursor == 0) SetPage(GM_SETTINGS);
            else if (cursor == 1) { CL_GraphicsMenu_Close(); Cbuf_AddText(cmd_local, "xbox_demo_start\n"); }
            else GameMenu();
        } else if (key != K_ENTER || !repeated) {
            /* Do not repeatedly flip toggles while a direction is held. */
            if (!(cursor == 0 && repeated)) Adjust(key == K_LEFTARROW ? -1 : 1, key == K_ENTER);
        }
    }
    return true; /* no gameplay bindings leak through the operations panel */
}
void CL_GraphicsMenu_LogSettings(void)
{
    unsigned i;
    Con_Printf("XBOX_GRAPHICS_PROFILE revision=%u quality=%s\n", revision, Value("cl_minfps") > 0 ? "adaptive" : "fixed");
    for (i = 0; i < GRAPHICS_SETTINGS; ++i)
        if (Available(settings[i].name)) Con_Printf("XBOX_GRAPHICS %s=%.9g\n", settings[i].name, (double)Value(settings[i].name));
}
qbool CL_GraphicsMenu_Draw(void)
{
#ifdef CONFIG_MENU
    unsigned first, end, i;
    float width, height, scale, x, y;
    char line[128];
    if (!CL_Attract_Enabled() || page == GM_CLOSED || key_dest != key_menu) return false;
    width = max(1, vid_conwidth.value);
    height = max(1, vid_conheight.value);
    scale = min(width / 640, height / 480);
    x = (width - 580 * scale) * 0.5f;
    y = (height - 400 * scale) * 0.5f;
    DrawQ_Fill(0, 0, width, height, 0, 0, 0, 0.92f, 0);
#define GM_TEXT(row, text, selected) DrawQ_String(x + 8*scale, y + (row)*20*scale, text, 70, 8*scale, 8*scale, 1, 1, (selected)?0.25f:1, 1, 0, NULL, true, FONT_DEFAULT)
    GM_TEXT(0, page == GM_HOME ? "XBOX BENCHMARK MENU" : "GRAPHICS SETTINGS", false);
    GM_TEXT(1, Value("cl_minfps") > 0 ? "Automatic quality: ON (adaptive workload)" : "Automatic quality: OFF (fixed workload)", false);
    if (page == GM_HOME) {
        const char *items[] = {"Graphics settings", "Restart demo loop", "Nexuiz game menu"};
        for (i = 0; i < 3; ++i) { dpsnprintf(line, sizeof(line), "%s%s", cursor == i ? "> " : "  ", items[i]); GM_TEXT(3+i, line, cursor == i); }
        GM_TEXT(12, "D-pad / left stick: browse    A: select", false);
        GM_TEXT(13, "B / Back: game menu    Start: demo loop", false);
        GM_TEXT(14, "Y from the game menu: return to this panel", false);
    } else {
        first = (cursor / GRAPHICS_PAGE_ROWS) * GRAPHICS_PAGE_ROWS;
        end = min(first + GRAPHICS_PAGE_ROWS, GRAPHICS_ROWS);
        for (i = first; i < end; ++i) {
            char value[32];
            const char *label;
            if (i < GRAPHICS_SETTINGS) {
                label = settings[i].label;
                if (!Available(settings[i].name)) dp_strlcpy(value, "Unavailable", sizeof(value));
                else if (i == 0) dp_strlcpy(value, Value("cl_minfps") > 0 ? "ON" : "OFF", sizeof(value));
                else if (settings[i].count == 2) dp_strlcpy(value, Value(settings[i].name) != 0 ? "ON" : "OFF", sizeof(value));
                else dpsnprintf(value, sizeof(value), "%.3g", (double)Value(settings[i].name));
            } else {
                label = i == GRAPHICS_SETTINGS ? "Apply texture changes (reload renderer)" : i == GRAPHICS_SETTINGS + 1 ? "Save graphics preferences" : "Back";
                dp_strlcpy(value, i == GRAPHICS_SETTINGS && texture_pending ? "Pending" : "", sizeof(value));
            }
            dpsnprintf(line, sizeof(line), "%s%-39s %s", cursor == i ? "> " : "  ", label, value);
            GM_TEXT(3+i-first, line, cursor == i);
        }
        if (cursor < GRAPHICS_SETTINGS) GM_TEXT(12, settings[cursor].help, false);
        dpsnprintf(line, sizeof(line), "Page %u/%u  D-pad/stick: browse  Left/Right: adjust", first/GRAPHICS_PAGE_ROWS+1, (GRAPHICS_ROWS+GRAPHICS_PAGE_ROWS-1)/GRAPHICS_PAGE_ROWS);
        GM_TEXT(14, line, false);
        GM_TEXT(15, "A: toggle/select   B / Back / Start: back", false);
    }
    GM_TEXT(17, message, false);
    GM_TEXT(19, "Effects depend on the active renderer and content.", false);
#undef GM_TEXT
    return true;
#else
    return false;
#endif
}
