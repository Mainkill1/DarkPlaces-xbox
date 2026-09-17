/* SPDX-License-Identifier: GPL-2.0-or-later
 * Force-included into repository-owned engine objects only, never nxdk itself.
 */
#ifndef DP_XBOX_GAME_PROFILE_H
#define DP_XBOX_GAME_PROFILE_H

#define DP_PLATFORM_XBOX 1
#define DP_XBOX_ENGINE_BOOTSTRAP 1
#define DP_SMALLMEMORY 1
#define USE_RWOPS 1
#define LINK_TO_ZLIB 1
#define LINK_TO_LIBJPEG 1
#define NOSUPPORTIPV6 1
#define THREADDISABLE 1
#define NO_SSE 1

/* The compiler uses the Win32 ABI. The engine must not select desktop WinSock,
 * shell folders, DLL loading, or desktop video backends on that account. */
#ifdef WIN32
#undef WIN32
#endif

#define DP_FS_BASEDIR "D:/"
#define DP_FS_USERDIR "E:/UDATA/4e585549/"

/* zlib/JPEG use the pinned SDK static libraries, not desktop DLL loading. */
#define DP_XBOX_PROFILE_NAME "engine-bootstrap"
#define DP_XBOX_MEMORY_TARGET_MIB 64

/* Capability bits remain evidence-backed runtime claims. Renderer source mode
 * is selected by xbox/game/Makefile through DP_XBOX_NATIVE_RENDERER or
 * DP_XBOX_RENDERER_BOOTSTRAP; neither source selection proves this bit. */
#define DP_XBOX_CAP_RENDERER 0
#define DP_XBOX_CAP_AUDIO 0
#define DP_XBOX_CAP_NETWORK 0

#endif
