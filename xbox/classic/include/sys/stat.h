#ifndef XBOX_CLASSIC_SYS_STAT_H
#define XBOX_CLASSIC_SYS_STAT_H

#include <sys/types.h>

#define S_IFREG 0100000
#define S_IFDIR 0040000
#define S_IREAD 0000400
#define S_IWRITE 0000200
#define S_ISDIR(mode) (((mode) & S_IFDIR) == S_IFDIR)

struct stat
{
	mode_t st_mode;
	off_t st_size;
};

int stat(const char *path, struct stat *information);
int mkdir(const char *path, mode_t mode);

#endif
