/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef DP_XBOX_PLATFORM_H
#define DP_XBOX_PLATFORM_H
#include <stddef.h>

/* All returned roots include a trailing slash; no caller owns these strings. */
int DP_XboxMain(void);
const char *DP_XboxContentRoot(void);
const char *DP_XboxWriteRoot(void);
int DP_XboxWritesAvailable(void);
void DP_XboxInitRoots(void);
int DP_XboxNativePath(char *out, size_t capacity, const char *path);
int DP_XboxPathType(const char *path); /* 0 missing, 1 regular file, 2 directory */
int DP_XboxMakeDirectory(const char *path);
int DP_XboxRemoveFile(const char *path);
void DP_XboxDebugWrite(const char *text, size_t length);
void DP_XboxSetDebugVideo(int ready);
void DP_XboxStage(const char *name);

#endif
