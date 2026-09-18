#include <limits.h>
#include <png.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "xbox_png.h"

typedef struct xbox_png_decode_s
{
	const unsigned char *input;
	size_t input_size;
	size_t input_offset;
	xbox_png_alloc_fn allocate;
	xbox_png_free_fn release;
	void *opaque;
	unsigned char *pixels;
	png_bytep *rows;
	char *error;
	size_t error_size;
} xbox_png_decode_t;

static void Xbox_PngSetError(xbox_png_decode_t *decode, const char *message)
{
	if (decode != NULL && decode->error != NULL && decode->error_size > 0)
	{
		snprintf(decode->error, decode->error_size, "%s",
			message != NULL ? message : "unknown libpng error");
	}
}

static void Xbox_PngError(png_structp png, png_const_charp message)
{
	xbox_png_decode_t *decode = (xbox_png_decode_t *)png_get_error_ptr(png);
	Xbox_PngSetError(decode, message);
	png_longjmp(png, 1);
}

static void Xbox_PngWarning(png_structp png, png_const_charp message)
{
	(void)png;
	(void)message;
}

static void Xbox_PngRead(png_structp png, png_bytep output, png_size_t length)
{
	xbox_png_decode_t *decode = (xbox_png_decode_t *)png_get_io_ptr(png);
	if (decode == NULL || length > decode->input_size - decode->input_offset)
		png_error(png, "truncated PNG input");
	memcpy(output, decode->input + decode->input_offset, length);
	decode->input_offset += length;
}

int Xbox_PngDecodeBGRA(const unsigned char *input, size_t input_size,
	xbox_png_alloc_fn allocate, xbox_png_free_fn release, void *opaque,
	xbox_png_image_t *image, char *error, size_t error_size)
{
	xbox_png_decode_t *decode;
	png_structp png = NULL;
	png_infop info = NULL;
	png_uint_32 width;
	png_uint_32 height;
	png_size_t row_bytes;
	size_t expected_row_bytes;
	size_t pixel_size;
	size_t rows_size;
	unsigned int y;
	int bit_depth;
	int color_type;
	int interlace_type;
	int result = 0;

	if (image != NULL)
		memset(image, 0, sizeof(*image));
	if (error != NULL && error_size > 0)
		error[0] = '\0';
	if (input == NULL || image == NULL || allocate == NULL || release == NULL)
	{
		if (error != NULL && error_size > 0)
			snprintf(error, error_size, "invalid PNG decode arguments");
		return 0;
	}
	if (input_size < 8 || png_sig_cmp(input, 0, 8) != 0)
	{
		if (error != NULL && error_size > 0)
			snprintf(error, error_size, "invalid PNG signature");
		return 0;
	}

	decode = (xbox_png_decode_t *)calloc(1, sizeof(*decode));
	if (decode == NULL)
	{
		if (error != NULL && error_size > 0)
			snprintf(error, error_size, "out of memory creating PNG decoder");
		return 0;
	}
	decode->input = input;
	decode->input_size = input_size;
	decode->allocate = allocate;
	decode->release = release;
	decode->opaque = opaque;
	decode->error = error;
	decode->error_size = error_size;

	png = png_create_read_struct(PNG_LIBPNG_VER_STRING, decode,
		Xbox_PngError, Xbox_PngWarning);
	if (png == NULL)
	{
		Xbox_PngSetError(decode, "libpng read-structure creation failed");
		goto cleanup;
	}
	info = png_create_info_struct(png);
	if (info == NULL)
	{
		Xbox_PngSetError(decode, "libpng info-structure creation failed");
		goto cleanup;
	}
	if (setjmp(png_jmpbuf(png)) != 0)
		goto cleanup;

	png_set_read_fn(png, decode, Xbox_PngRead);
	png_read_info(png, info);
	if (!png_get_IHDR(png, info, &width, &height, &bit_depth, &color_type,
		&interlace_type, NULL, NULL))
		png_error(png, "missing PNG image header");
	if (width == 0 || height == 0 || width > INT_MAX || height > INT_MAX)
		png_error(png, "unsupported PNG dimensions");

	if (bit_depth == 16)
		png_set_strip_16(png);
	if (color_type == PNG_COLOR_TYPE_PALETTE)
		png_set_palette_to_rgb(png);
	if (color_type == PNG_COLOR_TYPE_GRAY && bit_depth < 8)
		png_set_expand_gray_1_2_4_to_8(png);
	if (png_get_valid(png, info, PNG_INFO_tRNS))
		png_set_tRNS_to_alpha(png);
	if (color_type == PNG_COLOR_TYPE_GRAY || color_type == PNG_COLOR_TYPE_GRAY_ALPHA)
		png_set_gray_to_rgb(png);
	if (!(color_type & PNG_COLOR_MASK_ALPHA) && !png_get_valid(png, info, PNG_INFO_tRNS))
		png_set_filler(png, 0xff, PNG_FILLER_AFTER);
	png_set_bgr(png);
	(void)png_set_interlace_handling(png);
	png_read_update_info(png, info);

	row_bytes = png_get_rowbytes(png, info);
	if (png_get_bit_depth(png, info) != 8 || png_get_channels(png, info) != 4)
		png_error(png, "PNG did not normalize to 8-bit BGRA");
	expected_row_bytes = (size_t)width * 4;
	if (width != 0 && expected_row_bytes / 4 != (size_t)width)
		png_error(png, "PNG row size overflow");
	if (row_bytes != (png_size_t)expected_row_bytes)
		png_error(png, "invalid PNG row size");
	if (height != 0 && (size_t)row_bytes > SIZE_MAX / (size_t)height)
		png_error(png, "PNG image size overflow");
	pixel_size = (size_t)row_bytes * (size_t)height;
	rows_size = (size_t)height * sizeof(*decode->rows);
	if (height != 0 && rows_size / sizeof(*decode->rows) != (size_t)height)
		png_error(png, "PNG row table size overflow");

	decode->pixels = (unsigned char *)allocate(opaque, pixel_size);
	decode->rows = (png_bytep *)allocate(opaque, rows_size);
	if (decode->pixels == NULL || decode->rows == NULL)
		png_error(png, "out of memory decoding PNG");
	for (y = 0; y < (unsigned int)height; ++y)
		decode->rows[y] = decode->pixels + (size_t)y * row_bytes;
	png_read_image(png, decode->rows);
	png_read_end(png, info);

	image->pixels = decode->pixels;
	image->size = pixel_size;
	image->width = (unsigned int)width;
	image->height = (unsigned int)height;
	decode->pixels = NULL;
	result = 1;

cleanup:
	if (decode->rows != NULL)
		release(opaque, decode->rows);
	if (decode->pixels != NULL)
		release(opaque, decode->pixels);
	if (png != NULL)
		png_destroy_read_struct(&png, info != NULL ? &info : NULL, NULL);
	free(decode);
	return result;
}
