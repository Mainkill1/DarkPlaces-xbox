#ifndef XBOX_CLASSIC_PATH_H
#define XBOX_CLASSIC_PATH_H

#include <stddef.h>

#define XBOX_PATH_MAX 260

int Xbox_NormalizePath(const char *source, char *destination, size_t capacity);

#endif
