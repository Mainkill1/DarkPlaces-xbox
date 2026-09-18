#ifndef XBOX_CLASSIC_DIRENT_H
#define XBOX_CLASSIC_DIRENT_H

#define XBOX_DIRENT_NAME_MAX 260

typedef struct xbox_classic_dir_s DIR;

struct dirent
{
	char d_name[XBOX_DIRENT_NAME_MAX];
};

DIR *opendir(const char *path);
struct dirent *readdir(DIR *directory);
int closedir(DIR *directory);

#endif
