/* Minimal stat/mkdir surface consumed by the classic DarkPlaces filesystem. */

#include <errno.h>
#include <fileapi.h>
#include <string.h>
#include <sys/stat.h>
#include <winbase.h>

#include "include/xbox_path.h"

int stat(const char *path, struct stat *information)
{
	char normalized[MAX_PATH];
	WIN32_FILE_ATTRIBUTE_DATA attributes;

	if (!information || Xbox_NormalizePath(path, normalized, sizeof(normalized)) < 0)
	{
		if (!information)
			errno = EINVAL;
		return -1;
	}
	if (!GetFileAttributesEx(normalized, GetFileExInfoStandard, &attributes))
	{
		errno = ENOENT;
		return -1;
	}
	if (attributes.nFileSizeHigh)
	{
		errno = EFBIG;
		return -1;
	}
	information->st_mode = (attributes.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) ? S_IFDIR : S_IFREG;
	information->st_size = (off_t)attributes.nFileSizeLow;
	return 0;
}

int mkdir(const char *path, mode_t mode)
{
	char normalized[MAX_PATH];
	(void)mode;

	if (Xbox_NormalizePath(path, normalized, sizeof(normalized)) < 0)
		return -1;
	if (!CreateDirectory(normalized, NULL))
	{
		errno = EIO;
		return -1;
	}
	return 0;
}
