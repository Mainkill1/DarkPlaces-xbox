/* Bounded POSIX descriptor compatibility for the Nexuiz-era filesystem.
 * nxdk's PDCLib owns the underlying FILE streams; this layer only provides
 * the descriptor-shaped API expected by DarkPlaces.  Duplicates share a
 * stream position and retain the stream until the last descriptor closes. */

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include "include/xbox_posix_io.h"
#include "include/xbox_path.h"

#define XBOX_POSIX_MAX_DESCRIPTORS 64
#define XBOX_POSIX_FIRST_DESCRIPTOR 3

typedef struct xbox_posix_file_s
{
	FILE *stream;
	unsigned int references;
} xbox_posix_file_t;

static xbox_posix_file_t xbox_posix_files[XBOX_POSIX_MAX_DESCRIPTORS];
static xbox_posix_file_t *xbox_posix_descriptors[XBOX_POSIX_MAX_DESCRIPTORS];

static int Xbox_PosixAllocateDescriptor(xbox_posix_file_t *file)
{
	int fd;

	for (fd = XBOX_POSIX_FIRST_DESCRIPTOR; fd < XBOX_POSIX_MAX_DESCRIPTORS; ++fd)
		if (!xbox_posix_descriptors[fd])
		{
			xbox_posix_descriptors[fd] = file;
			++file->references;
			return fd;
		}
	errno = EMFILE;
	return -1;
}

static xbox_posix_file_t *Xbox_PosixGetFile(int fd)
{
	if (fd < XBOX_POSIX_FIRST_DESCRIPTOR || fd >= XBOX_POSIX_MAX_DESCRIPTORS || !xbox_posix_descriptors[fd])
	{
		errno = EBADF;
		return NULL;
	}
	return xbox_posix_descriptors[fd];
}

static const char *Xbox_PosixOpenMode(int flags)
{
	if ((flags & O_RDWR) == O_RDWR)
	{
		if (flags & O_TRUNC)
			return "w+b";
		return "r+b";
	}
	if (flags & O_WRONLY)
	{
		if (flags & O_APPEND)
			return "ab";
		if (flags & O_TRUNC)
			return "wb";
		return "r+b";
	}
	return "rb";
}

int open(const char *path, int flags, ...)
{
	char normalized[XBOX_PATH_MAX];
	xbox_posix_file_t *file = NULL;
	FILE *stream;
	int i;
	int fd;

	if (Xbox_NormalizePath(path, normalized, sizeof(normalized)) < 0)
		return -1;

	if ((flags & (O_CREAT | O_EXCL)) == (O_CREAT | O_EXCL))
	{
		stream = fopen(normalized, "rb");
		if (stream)
		{
			fclose(stream);
			errno = EEXIST;
			return -1;
		}
	}

	stream = fopen(normalized, Xbox_PosixOpenMode(flags));
	if (!stream && (flags & O_CREAT) && !(flags & O_TRUNC))
		stream = fopen(normalized, (flags & O_RDWR) ? "w+b" : "wb");
	if (!stream)
		return -1;

	for (i = 0; i < XBOX_POSIX_MAX_DESCRIPTORS; ++i)
		if (!xbox_posix_files[i].stream)
		{
			file = &xbox_posix_files[i];
			break;
		}
	if (!file)
	{
		fclose(stream);
		errno = EMFILE;
		return -1;
	}

	file->stream = stream;
	file->references = 0;
	fd = Xbox_PosixAllocateDescriptor(file);
	if (fd < 0)
	{
		fclose(stream);
		file->stream = NULL;
	}
	return fd;
}

int close(int fd)
{
	xbox_posix_file_t *file = Xbox_PosixGetFile(fd);
	int result = 0;

	if (!file)
		return -1;
	xbox_posix_descriptors[fd] = NULL;
	if (--file->references == 0)
	{
		result = fclose(file->stream);
		file->stream = NULL;
	}
	return result;
}

int dup(int fd)
{
	xbox_posix_file_t *file = Xbox_PosixGetFile(fd);
	return file ? Xbox_PosixAllocateDescriptor(file) : -1;
}

off_t lseek(int fd, off_t offset, int whence)
{
	xbox_posix_file_t *file = Xbox_PosixGetFile(fd);
	long position;

	if (!file)
		return (off_t)-1;
	if (fseek(file->stream, (long)offset, whence) != 0)
		return (off_t)-1;
	position = ftell(file->stream);
	return position < 0 ? (off_t)-1 : (off_t)position;
}

ssize_t read(int fd, void *buffer, size_t count)
{
	xbox_posix_file_t *file = Xbox_PosixGetFile(fd);
	size_t result;

	if (!file)
		return -1;
	result = fread(buffer, 1, count, file->stream);
	if (result == 0 && ferror(file->stream))
		return -1;
	return (ssize_t)result;
}

ssize_t write(int fd, const void *buffer, size_t count)
{
	xbox_posix_file_t *file = Xbox_PosixGetFile(fd);
	size_t result;

	if (!file)
		return -1;
	result = fwrite(buffer, 1, count, file->stream);
	if (result == 0 && ferror(file->stream))
		return -1;
	return (ssize_t)result;
}

int unlink(const char *path)
{
	char normalized[XBOX_PATH_MAX];

	if (Xbox_NormalizePath(path, normalized, sizeof(normalized)) < 0)
		return -1;
	return remove(normalized);
}
