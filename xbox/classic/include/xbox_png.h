#ifndef XBOX_PNG_H
#define XBOX_PNG_H

#include <stddef.h>

typedef void *(*xbox_png_alloc_fn)(void *opaque, size_t size);
typedef void (*xbox_png_free_fn)(void *opaque, void *address);

typedef struct xbox_png_image_s
{
	unsigned char *pixels;
	size_t size;
	unsigned int width;
	unsigned int height;
} xbox_png_image_t;

int Xbox_PngDecodeBGRA(const unsigned char *input, size_t input_size,
	xbox_png_alloc_fn allocate, xbox_png_free_fn release, void *opaque,
	xbox_png_image_t *image, char *error, size_t error_size);

#endif
