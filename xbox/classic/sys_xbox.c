#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <windows.h>
#include <hal/debug.h>
#include <hal/video.h>
#include <nxdk/net.h>
#include <SDL.h>
#include <zlib.h>
#include <png.h>
#include <vorbis/codec.h>
#include <vorbis/vorbisfile.h>

#include "quakedef.h"
#include "include/xbox_boot_trace.h"
#include "include/xbox_network.h"
#include "include/xbox_storage.h"

#define XBOX_BASEDIR "D:/"
#define XBOX_USERDIR "E:/UDATA/Nexuiz"
#define XBOX_BOOT_TRACE "E:\\UDATA\\Nexuiz\\boot-trace.txt"

static void *Xbox_StaticSymbol(const char *name)
{
	/* zlib: PK3 loading/writing */
	if (!strcmp(name, "inflate")) return (void *)inflate;
	if (!strcmp(name, "inflateEnd")) return (void *)inflateEnd;
	if (!strcmp(name, "inflateInit2_")) return (void *)inflateInit2_;
	if (!strcmp(name, "inflateReset")) return (void *)inflateReset;
	if (!strcmp(name, "deflateInit2_")) return (void *)deflateInit2_;
	if (!strcmp(name, "deflateEnd")) return (void *)deflateEnd;
	if (!strcmp(name, "deflate")) return (void *)deflate;

	/* libpng: Nexuiz HUD/menu/world textures. */
	if (!strcmp(name, "png_set_sig_bytes")) return (void *)png_set_sig_bytes;
	if (!strcmp(name, "png_sig_cmp")) return (void *)png_sig_cmp;
	if (!strcmp(name, "png_create_read_struct")) return (void *)png_create_read_struct;
	if (!strcmp(name, "png_create_info_struct")) return (void *)png_create_info_struct;
	if (!strcmp(name, "png_read_info")) return (void *)png_read_info;
	if (!strcmp(name, "png_set_expand")) return (void *)png_set_expand;
	if (!strcmp(name, "png_set_gray_1_2_4_to_8")) return (void *)png_set_expand_gray_1_2_4_to_8;
	if (!strcmp(name, "png_set_palette_to_rgb")) return (void *)png_set_palette_to_rgb;
	if (!strcmp(name, "png_set_tRNS_to_alpha")) return (void *)png_set_tRNS_to_alpha;
	if (!strcmp(name, "png_set_gray_to_rgb")) return (void *)png_set_gray_to_rgb;
	if (!strcmp(name, "png_set_filler")) return (void *)png_set_filler;
	if (!strcmp(name, "png_read_update_info")) return (void *)png_read_update_info;
	if (!strcmp(name, "png_read_image")) return (void *)png_read_image;
	if (!strcmp(name, "png_read_end")) return (void *)png_read_end;
	if (!strcmp(name, "png_destroy_read_struct")) return (void *)png_destroy_read_struct;
	if (!strcmp(name, "png_set_read_fn")) return (void *)png_set_read_fn;
	if (!strcmp(name, "png_get_valid")) return (void *)png_get_valid;
	if (!strcmp(name, "png_get_rowbytes")) return (void *)png_get_rowbytes;
	if (!strcmp(name, "png_get_channels")) return (void *)png_get_channels;
	if (!strcmp(name, "png_get_bit_depth")) return (void *)png_get_bit_depth;
	if (!strcmp(name, "png_get_IHDR")) return (void *)png_get_IHDR;
	if (!strcmp(name, "png_get_libpng_ver")) return (void *)png_get_libpng_ver;

	/* libvorbis/libvorbisfile: Nexuiz sound effects and music. */
	if (!strcmp(name, "ov_clear")) return (void *)ov_clear;
	if (!strcmp(name, "ov_info")) return (void *)ov_info;
	if (!strcmp(name, "ov_comment")) return (void *)ov_comment;
	if (!strcmp(name, "ov_open_callbacks")) return (void *)ov_open_callbacks;
	if (!strcmp(name, "ov_pcm_seek")) return (void *)ov_pcm_seek;
	if (!strcmp(name, "ov_pcm_total")) return (void *)ov_pcm_total;
	if (!strcmp(name, "ov_read")) return (void *)ov_read;
	if (!strcmp(name, "vorbis_comment_query")) return (void *)vorbis_comment_query;
	return NULL;
}

qboolean Sys_LoadLibrary(const char **dllnames, dllhandle_t *handle, const dllfunction_t *fcts)
{
	const dllfunction_t *func;
	(void)dllnames;
	if (!handle)
		return false;
	for (func = fcts; func && func->name; ++func)
	{
		void *p = Xbox_StaticSymbol(func->name);
		if (!p)
		{
			const dllfunction_t *clear;
			for (clear = fcts; clear && clear->name; ++clear)
				*clear->funcvariable = NULL;
			*handle = NULL;
			return false;
		}
		*func->funcvariable = p;
	}
	*handle = (dllhandle_t)1;
	return true;
}

void Sys_UnloadLibrary(dllhandle_t *handle)
{
	if (handle)
		*handle = NULL;
}

void *Sys_GetProcAddress(dllhandle_t handle, const char *name)
{
	(void)handle;
	return Xbox_StaticSymbol(name);
}

char *Sys_TimeString(const char *timeformat)
{
	static char text[128];
	time_t now = time(NULL);
	struct tm *tmv = localtime(&now);
	if (!tmv || !strftime(text, sizeof(text), timeformat, tmv))
		text[0] = 0;
	return text;
}

void Sys_Shutdown(void)
{
	Xbox_BootTraceMark("Sys_Shutdown");
	fflush(stdout);
	SDL_Quit();
	Xbox_ShutdownNetwork();
	Xbox_BootTraceClose();
}

void Sys_Error(const char *error, ...)
{
	va_list argptr;
	char string[MAX_INPUTLINE];
	va_start(argptr, error);
	dpvsnprintf(string, sizeof(string), error, argptr);
	va_end(argptr);
	debugPrint("NEXUIZ XBOX FATAL: %s\n", string);
	Xbox_BootTraceMark("FATAL: %s", string);
	Con_Printf("Nexuiz Xbox fatal: %s\n", string);
	Host_Shutdown();
	Sys_Shutdown();
	Sleep(5000);
	exit(1);
}

void Sys_PrintToTerminal(const char *text)
{
	if (text && *text)
	{
		Xbox_BootTraceWrite(text);
		debugPrint("%s", text);
	}
}

void Sys_Quit(int returnvalue)
{
	Host_Shutdown();
	Sys_Shutdown();
	exit(returnvalue);
}

void Sys_AllowProfiling(qboolean enable)
{
	(void)enable;
}

double Sys_DoubleTime(void)
{
	static Uint64 start;
	Uint64 now;
	Uint64 freq = SDL_GetPerformanceFrequency();
	if (!start)
		start = SDL_GetPerformanceCounter();
	now = SDL_GetPerformanceCounter();
	if (!freq)
		return (double)SDL_GetTicks() * 0.001;
	return (double)(now - start) / (double)freq;
}

char *Sys_ConsoleInput(void)
{
	return NULL;
}

void Sys_Sleep(int microseconds)
{
	if (microseconds > 0)
		SDL_Delay((Uint32)((microseconds + 999) / 1000));
}

char *Sys_GetClipboardData(void)
{
	return NULL;
}

void Sys_InitConsole(void)
{
}

void Sys_Init_Commands(void)
{
}

int main(int argc, char **argv)
{
	static char arg0[] = "nexuiz-xbox";
	static char arg1[] = "-nexuiz";
	static char arg2[] = "-basedir";
	static char arg3[] = XBOX_BASEDIR;
	static char arg4[] = "-userdir";
	static char arg5[] = XBOX_USERDIR;
	static char arg6[] = "-fullscreen";
	static char arg7[] = "-width";
	static char arg8[] = "640";
	static char arg9[] = "-height";
	static char arg10[] = "480";
	static char arg11[] = "-bpp";
	static char arg12[] = "32";
	static char *xargv[] = {arg0,arg1,arg2,arg3,arg4,arg5,arg6,arg7,arg8,arg9,arg10,arg11,arg12,NULL};
	(void)argc;
	(void)argv;

	XVideoSetMode(640, 480, 32, REFRESH_DEFAULT);
	debugClearScreen();
	if (Xbox_MountWritableStorage() == 0)
	{
		CreateDirectory("E:\\UDATA", NULL);
		CreateDirectory("E:\\UDATA\\Nexuiz", NULL);
		Xbox_BootTraceOpen(XBOX_BOOT_TRACE);
	}
	Xbox_BootTraceMark("main entered; debug framebuffer active");
	debugPrint("Nexuiz Xbox: starting DarkPlaces...\n");
	debugPrint("Nexuiz Xbox: basedir=D:/ userdir=E:/UDATA/Nexuiz\n");

	/* The disc root is read-only game content. DarkPlaces' existing -userdir
	 * support adds userdir/data after basedir/data, so saved config, demos,
	 * screenshots and progression writes land on E: while packaged PK3s remain
	 * readable from D:. FS_CreatePath creates the writable hierarchy lazily. */
	com_argc = 13;
	com_argv = (const char **)xargv;
	SDL_Init(0);
	Xbox_BootTraceMark("SDL base initialized; scheduling nxdk network");
	Xbox_StartNetworkAsync();
	Xbox_BootTraceMark("entering Host_Main");
	Host_Main();
	return 0;
}
