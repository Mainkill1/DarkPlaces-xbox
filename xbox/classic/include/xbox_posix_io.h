#ifndef XBOX_CLASSIC_POSIX_IO_H
#define XBOX_CLASSIC_POSIX_IO_H

#include <stddef.h>
#include <sys/types.h>

#define O_RDONLY   0x0000
#define O_WRONLY   0x0001
#define O_RDWR     0x0002
#define O_APPEND   0x0008
#define O_CREAT    0x0100
#define O_TRUNC    0x0200
#define O_EXCL     0x0400
#define O_NONBLOCK 0x4000
#define O_BINARY   0x8000

int open(const char *path, int flags, ...);
int close(int fd);
int dup(int fd);
off_t lseek(int fd, off_t offset, int whence);
ssize_t read(int fd, void *buffer, size_t count);
ssize_t write(int fd, const void *buffer, size_t count);
int unlink(const char *path);

#endif
