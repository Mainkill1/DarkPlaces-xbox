#ifndef DP_XBOX_CONFIG_H
#define DP_XBOX_CONFIG_H

#include <limits.h>
#include <stdint.h>

/*
 * Central compile profile for the first Original Xbox foundation target.
 * This header describes reality; unavailable subsystems must not pretend to
 * succeed. Later implementation slices may change individual capability bits
 * only when their acceptance evidence exists.
 */
#define DP_PLATFORM_XBOX 1
#define DP_XBOX_BENCHMARK 1
#define DP_SMALLMEMORY 1

#define DP_XBOX_PROFILE_NAME "foundation"
#define DP_XBOX_MEMORY_TARGET_MIB 64

#define DP_XBOX_CAP_RENDERER 0
#define DP_XBOX_CAP_AUDIO 0
#define DP_XBOX_CAP_NETWORK 0
#define DP_XBOX_CAP_DYNAMIC_LOADING 0
#define DP_XBOX_CAP_FILESYSTEM_WRITE 0
#define DP_XBOX_CAP_CONTROLLER_INPUT 0

#ifndef DP_XBOX_SOURCE_REVISION
#define DP_XBOX_SOURCE_REVISION "unknown"
#endif

#ifndef DP_XBOX_NXDK_REVISION
#define DP_XBOX_NXDK_REVISION "unverified"
#endif

#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
_Static_assert(CHAR_BIT == 8, "The Xbox port requires 8-bit bytes");
_Static_assert(sizeof(uint16_t) == 2, "The Xbox port requires 16-bit uint16_t");
_Static_assert(sizeof(uint32_t) == 4, "The Xbox port requires 32-bit uint32_t");
#if defined(__i386__)
_Static_assert(sizeof(void *) == 4, "The Original Xbox target requires 32-bit pointers");
#endif
#endif

#endif
