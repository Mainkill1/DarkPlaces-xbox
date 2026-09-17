/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native engine process owner. This replaces sys_shared.c in xbox/game only;
 * it calls the real Host_Init/Host_Frame, never a replacement game loop.
 */
#include <windows.h>
#include <SDL.h>
#include <stdarg.h>
#include <stdio.h>
#include <time.h>
#include "quakedef.h"
#include "xbox/platform/platform.h"
#include "xbox/platform/network.h"
#include "xbox/controller_sdl.h"
#include "xbox_build_identity.h"

#if !defined(DP_PLATFORM_XBOX)
#error sys_xbox.c belongs only to the native Xbox engine target
#endif
#ifdef main
#undef main
#endif

sys_t sys;
qbool sys_supportsdlgetticks = true;
cvar_t sys_usenoclockbutbenchmark = {CF_SHARED | CF_READONLY,
    "sys_usenoclockbutbenchmark", "0", "Synthetic clock is unavailable in the native engine bootstrap"};
cvar_t sys_libdir = {CF_SHARED | CF_READONLY, "sys_libdir", "", "Xbox dependencies are linked statically"};
static cvar_t sys_stdout = {CF_SHARED, "sys_stdout", "1", "Emit kernel diagnostics"};
static qbool platform_initialized;
static Uint64 counter_origin;
static Uint64 counter_frequency;

void Sys_Print(const char *text, size_t length)
{
    if (sys_stdout.integer) DP_XboxDebugWrite(text, length);
}

void Sys_Printf(const char *format, ...)
{
    char text[2048];
    int length;
    va_list args;
    va_start(args, format);
    length = vsnprintf(text, sizeof(text), format, args);
    va_end(args);
    if (length > 0)
        Sys_Print(text, (size_t)length < sizeof(text) ? (size_t)length : sizeof(text) - 1);
}

void Sys_Error(const char *format, ...)
{
    /* Fatal reporting cannot depend on a fully initialized engine, filesystem,
     * or renderer. Do not recurse into Host_Shutdown during a partial init. */
    char text[2048];
    int length;
    va_list args;
    host.state = host_failed;
    DP_XboxStage("fatal");
    va_start(args, format);
    length = vsnprintf(text, sizeof(text), format, args);
    va_end(args);
    if (length > 0)
        DP_XboxDebugWrite(text, (size_t)length < sizeof(text) ? (size_t)length : sizeof(text) - 1);
    DP_XboxDebugWrite("\nExecution stopped; this is not a playable build.\n",
        sizeof("\nExecution stopped; this is not a playable build.\n") - 1);
    for (;;) Sleep(100);
}

int Sys_CheckParm(const char *parameter)
{
    int i;
    for (i = 1; i < sys.argc; ++i)
        if (sys.argv[i] && !strcmp(parameter, sys.argv[i])) return i;
    return 0;
}

void Sys_Init_Commands(void)
{
    Cvar_RegisterVariable(&sys_stdout);
    Cvar_RegisterVariable(&sys_libdir);
    Cvar_RegisterVariable(&sys_usenoclockbutbenchmark);
}

void Sys_SDL_Init(void)
{
    if (platform_initialized) return;
    /* Only timer/events/controller services: no SDL desktop window or GL. */
    if (SDL_Init(SDL_INIT_TIMER | SDL_INIT_GAMECONTROLLER) != 0)
        Sys_Error("Xbox SDL service initialization failed: %s", SDL_GetError());
    counter_frequency = SDL_GetPerformanceFrequency();
    counter_origin = SDL_GetPerformanceCounter();
    if (!counter_frequency) Sys_Error("Xbox performance counter has zero frequency");
    platform_initialized = true;
}

void Sys_SDL_Shutdown(void)
{
    DP_XboxNetworkStop();
    DP_ControllerSDL_Shutdown();
    if (platform_initialized) SDL_Quit();
    platform_initialized = false;
}

unsigned int Sys_SDL_GetTicks(void) { return SDL_GetTicks(); }
void Sys_SDL_Delay(unsigned int milliseconds) { Sleep(milliseconds); }
char *Sys_SDL_GetClipboardData(void) { return NULL; }
char *Sys_ConsoleInput(void) { return NULL; }

void Sys_SDL_Dialog(const char *title, const char *text)
{
    DP_XboxDebugWrite(title, strlen(title));
    DP_XboxDebugWrite(": ", 2);
    DP_XboxDebugWrite(text, strlen(text));
    DP_XboxDebugWrite("\n", 1);
}

size_t Sys_TimeString(char *buffer, size_t capacity, const char *format)
{
    time_t now;
    struct tm *calendar;
    size_t length;
    if (!buffer || !capacity) return 0;
    buffer[0] = '\0';
    now = time(NULL);
    calendar = localtime(&now);
    if (!calendar) return 0;
    length = strftime(buffer, capacity, format, calendar);
    if (!length) buffer[0] = '\0';
    return length;
}

/* Dynamic services stay explicitly unavailable. Optional callers already have
 * failure paths. zlib/JPEG use their direct static interfaces; other dynamic
 * codec dependencies remain unavailable until explicitly registered. */
qbool Sys_LoadSelf(dllhandle_t *handle)
{
    if (handle) *handle = NULL;
    return false;
}
qbool Sys_LoadLibrary(const char *name, dllhandle_t *handle)
{
    (void)name;
    if (handle) *handle = NULL;
    return false;
}
qbool Sys_LoadDependency(const char **names, dllhandle_t *handle, const dllfunction_t *functions)
{
    const dllfunction_t *function;
    (void)names;
    if (handle) *handle = NULL;
    for (function = functions; function && function->name; ++function)
        if (function->funcvariable) *function->funcvariable = NULL;
    return false;
}
void Sys_FreeLibrary(dllhandle_t *handle) { if (handle) *handle = NULL; }
void *Sys_GetProcAddress(dllhandle_t handle, const char *name)
{
    (void)handle; (void)name;
    return NULL;
}
void Sys_AllowProfiling(qbool enable) { (void)enable; }
void Sys_ProvideSelfFD(void) { sys.selffd = -1; }
void Sys_InitProcessNice(void) { sys.nicepossible = false; }
void Sys_MakeProcessNice(void) { }
void Sys_MakeProcessMean(void) { }

double Sys_DirtyTime(void)
{
    Uint64 current;
    if (!platform_initialized) Sys_SDL_Init();
    current = SDL_GetPerformanceCounter();
    if (current < counter_origin) return 0;
    return (double)(current - counter_origin) / (double)counter_frequency;
}

double Sys_Sleep(double seconds)
{
    double before, elapsed;
    DWORD milliseconds;
    if (!(seconds > 0) || host.restless) return 0;
    if (seconds > 0.999) seconds = 0.999;
    milliseconds = (DWORD)(seconds * 1000.0);
    before = Sys_DirtyTime();
    Sleep(milliseconds);
    elapsed = Sys_DirtyTime() - before;
    return elapsed >= 0 && elapsed < 1800 ? elapsed : 0;
}

int Sys_Main(int argc, char **argv)
{
    double time, newtime, wait;
    sys.argc = argc;
    sys.argv = (const char **)argv;
    sys.selffd = -1;
    sys.outfd = -1;
    sys_stdout.integer = 1;
    sys_stdout.value = 1;
    Host_Init();
    DP_XboxStage("host-init-returned");
    Sys_Printf("XBOX_GAME_HOST_INIT\nprofile=%s source=%s dirty=%d nxdk=%s\n",
        DP_XBOX_PROFILE_NAME, DP_XBOX_SOURCE_REVISION, DP_XBOX_SOURCE_DIRTY,
        DP_XBOX_NXDK_REVISION);
#ifdef DP_XBOX_NATIVE_RENDERER
    Sys_Printf("ENGINE BRINGUP: renderer=native-video audio=null LAN=transport-only\n");
#else
    Sys_Printf("ENGINE BOOTSTRAP: renderer=unimplemented audio=null LAN=transport-only\n");
#endif
    DP_XboxStage("frame-loop");
    for (;;) {
        DP_XboxNetworkPoll();
        if (setjmp(host.abortframe)) host.state = host_active;
        if (host.state >= host_shutdown) {
            Host_Shutdown();
            return 0;
        }
        newtime = Sys_DirtyTime();
        time = newtime - host.dirtytime;
        if (!(time >= 0 && time < 1800)) time = 0;
        host.realtime += time;
        host.dirtytime = newtime;
        wait = Host_Frame(time) - (Sys_DirtyTime() - host.dirtytime);
        host.sleeptime = Sys_Sleep(wait);
    }
}

int DP_XboxMain(void)
{
    char *arguments[12];
    int count = 0;
    /* Native video mode and pbkit ownership belong to vid_xbox.c. Early
     * startup remains diagnosable through DbgPrint before the renderer exists. */
    DP_XboxSetDebugVideo(0);
    DP_XboxStage("entry");
    DP_XboxInitRoots();
    if (!DP_XboxContentRoot()[0]) Sys_Error("Cannot determine the executable content root");
    arguments[count++] = "default.xbe";
    arguments[count++] = "-nexuiz";
    arguments[count++] = "-xboxbenchmark";
    arguments[count++] = "-basedir";
    arguments[count++] = (char *)DP_XboxContentRoot();
    if (!DP_XboxWritesAvailable()) arguments[count++] = "-readonly";
    arguments[count] = NULL;
    return Sys_Main(count, arguments);
}
