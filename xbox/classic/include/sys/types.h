#ifndef XBOX_CLASSIC_SYS_TYPES_H
#define XBOX_CLASSIC_SYS_TYPES_H

#include <stddef.h>
#include <stdint.h>

/* Minimal POSIX names consumed by the 2009 DarkPlaces sources.  FATX and the
 * selected Nexuiz 2.5.2 package stay below the 2 GiB signed file limit. */
typedef int32_t off_t;
typedef int32_t ssize_t;
typedef uint32_t mode_t;
typedef uint32_t uid_t;
typedef uint32_t gid_t;

#endif
