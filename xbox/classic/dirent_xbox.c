/* Minimal directory iteration for the Xbox filesystem. */

#include <dirent.h>
#include <errno.h>
#include <fileapi.h>
#include <stdlib.h>
#include <string.h>
#include <winbase.h>

#include "include/xbox_path.h"

struct xbox_classic_dir_s
{
	HANDLE handle;
	WIN32_FIND_DATAA find_data;
	struct dirent entry;
	int first_pending;
};

DIR *opendir(const char *path)
{
	char pattern[MAX_PATH];
	size_t length;
	DIR *directory;

	if (!path)
	{
		errno = EINVAL;
		return NULL;
	}
	length = strlen(path);
	if (!length || length + 2 >= sizeof(pattern) ||
	    Xbox_NormalizePath(path, pattern, sizeof(pattern)) < 0)
	{
		errno = ENAMETOOLONG;
		return NULL;
	}
	length = strlen(pattern);

	if (length && pattern[length - 1] != '\\')
		pattern[length++] = '\\';
	pattern[length++] = '*';
	pattern[length] = '\0';

	directory = (DIR *)calloc(1, sizeof(*directory));
	if (!directory)
		return NULL;
	directory->handle = FindFirstFile(pattern, &directory->find_data);
	if (directory->handle == INVALID_HANDLE_VALUE)
	{
		free(directory);
		errno = ENOENT;
		return NULL;
	}
	directory->first_pending = 1;
	return directory;
}

struct dirent *readdir(DIR *directory)
{
	if (!directory)
	{
		errno = EBADF;
		return NULL;
	}
	if (directory->first_pending)
		directory->first_pending = 0;
	else if (!FindNextFile(directory->handle, &directory->find_data))
		return NULL;

	strncpy(directory->entry.d_name, directory->find_data.cFileName, sizeof(directory->entry.d_name) - 1);
	directory->entry.d_name[sizeof(directory->entry.d_name) - 1] = '\0';
	return &directory->entry;
}

int closedir(DIR *directory)
{
	int result;

	if (!directory)
	{
		errno = EBADF;
		return -1;
	}
	result = FindClose(directory->handle) ? 0 : -1;
	free(directory);
	return result;
}
