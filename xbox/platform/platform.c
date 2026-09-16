/* SPDX-License-Identifier: GPL-2.0-or-later
 * OS-only helpers. They do not allocate from the engine, call Con_Printf, or
 * perform renderer work, so they remain usable before Host_Init and on failure.
 */
#include <windows.h>
#include <xboxkrnl/xboxkrnl.h>
#include <hal/debug.h>
#include <stdio.h>
#include <string.h>
#include "platform.h"

#define PATH_CAPACITY 1024
static char content_root[PATH_CAPACITY] = "";
static const char write_root[] = "E:/UDATA/4e585549/";
static int writable;
static int debug_video;

const char *DP_XboxContentRoot(void) { return content_root; }
const char *DP_XboxWriteRoot(void) { return write_root; }
int DP_XboxWritesAvailable(void) { return writable; }
void DP_XboxSetDebugVideo(int ready) { debug_video = ready != 0; }

int DP_XboxNativePath(char *out, size_t capacity, const char *path)
{
    size_t i, length;
    if (!out || !capacity || !path) return 0;
    length = strlen(path);
    if (length >= capacity) { out[0] = '\0'; return 0; }
    for (i = 0; i < length; ++i)
        out[i] = path[i] == '/' ? '\\' : path[i];
    out[length] = '\0';
    return 1;
}

int DP_XboxPathType(const char *path)
{
    char native[PATH_CAPACITY];
    DWORD attributes;
    if (!DP_XboxNativePath(native, sizeof(native), path)) return 0;
    attributes = GetFileAttributesA(native);
    if (attributes == INVALID_FILE_ATTRIBUTES) return 0;
    return (attributes & FILE_ATTRIBUTE_DIRECTORY) ? 2 : 1;
}

int DP_XboxMakeDirectory(const char *path)
{
    char native[PATH_CAPACITY];
    if (!DP_XboxNativePath(native, sizeof(native), path)) return 0;
    if (CreateDirectoryA(native, NULL)) return 1;
    return DP_XboxPathType(path) == 2;
}

int DP_XboxRemoveFile(const char *path)
{
    char native[PATH_CAPACITY];
    if (!DP_XboxNativePath(native, sizeof(native), path)) return -1;
    return DeleteFileA(native) ? 0 : -1;
}

void DP_XboxDebugWrite(const char *text, size_t length)
{
    /* Format strings never originate in game content. Break long writes into
     * bounded blocks and always retain a kernel-debug channel when video fails.
     * This is not a claim that xemu routes DbgPrint into its normal stdout. */
    char block[256];
    size_t count;
    while (text && length) {
        count = length < sizeof(block) - 1 ? length : sizeof(block) - 1;
        memcpy(block, text, count);
        block[count] = '\0';
        DbgPrint("%s", block);
        if (debug_video) debugPrint("%s", block);
        text += count;
        length -= count;
    }
}

void DP_XboxStage(const char *name)
{
    char line[160];
    int length = snprintf(line, sizeof(line), "XBOX_GAME_STAGE=%s\n", name);
    if (length > 0)
        DP_XboxDebugWrite(line, (size_t)length < sizeof(line) ? (size_t)length : sizeof(line) - 1);
}

void DP_XboxInitRoots(void)
{
    char executable[PATH_CAPACITY];
    char native[PATH_CAPACITY];
    char *slash;
    FILE *probe;
    size_t i, length;
    int written, closed;

    /* Use the real NT executable path; nxdk file IO accepts \Device\ paths.
     * Bounds-check the kernel string rather than using an unbounded path copy.
     * Forward slashes are the VFS representation; NativePath restores NT form. */
    length = XeImageFileName->Length;
    if (!length || length >= sizeof(executable)) {
        DP_XboxDebugWrite("Invalid executable-root path\n", sizeof("Invalid executable-root path\n") - 1);
        return;
    }
    memcpy(executable, XeImageFileName->Buffer, length);
    executable[length] = '\0';
    slash = strrchr(executable, '\\');
    if (!slash) return;
    slash[1] = '\0';
    for (i = 0; executable[i]; ++i)
        if (executable[i] == '\\') executable[i] = '/';
    memcpy(content_root, executable, strlen(executable) + 1);

    writable = DP_XboxMakeDirectory("E:/UDATA") &&
               DP_XboxMakeDirectory("E:/UDATA/4e585549") &&
               DP_XboxMakeDirectory("E:/UDATA/4e585549/data");
    if (!writable) return;
    if (!DP_XboxNativePath(native, sizeof(native), "E:/UDATA/4e585549/.write-probe")) {
        writable = 0;
        return;
    }
    probe = fopen(native, "wb");
    if (!probe) { writable = 0; return; }
    written = fwrite("nx", 1, 2, probe) == 2;
    closed = fclose(probe) == 0;
    writable = written && closed;
    DP_XboxRemoveFile("E:/UDATA/4e585549/.write-probe");
}
