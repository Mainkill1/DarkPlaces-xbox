#include <stdint.h>
#include <stdlib.h>

#include "xbox_gl_upload.h"
#include "xbox_memory_profile.h"

/* Keep transient conversion memory bounded on the stock 64 MiB target. */
#define XBOX_GL_BGRA_STAGING_LIMIT (16U * 1024U * 1024U)

static void Xbox_GLUploadImage2D(xbox_gl_tex_image_2d_fn upload,
	GLenum target, GLint level, GLint internalformat, GLsizei width,
	GLsizei height, GLint border, GLenum format, GLenum type,
	const GLvoid *pixels)
{
	if (level == 0)
		Xbox_MemoryTraceTextureUpload("image2d", "before", level, width, height);
	upload(target, level, internalformat, width, height, border,
		format, type, pixels);
	if (level == 0)
		Xbox_MemoryTraceTextureUpload("image2d", "after", level, width, height);
}

static void Xbox_GLUploadSubImage2D(xbox_gl_tex_sub_image_2d_fn upload,
	GLenum target, GLint level, GLint xoffset, GLint yoffset, GLsizei width,
	GLsizei height, GLenum format, GLenum type, const GLvoid *pixels)
{
	if (level == 0)
		Xbox_MemoryTraceTextureUpload("subimage2d", "before", level, width, height);
	upload(target, level, xoffset, yoffset, width, height, format, type, pixels);
	if (level == 0)
		Xbox_MemoryTraceTextureUpload("subimage2d", "after", level, width, height);
}

static unsigned char *Xbox_GLConvertBGRA(const GLvoid *pixels,
	GLsizei width, GLsizei height)
{
	const unsigned char *source = (const unsigned char *)pixels;
	unsigned char *converted;
	size_t pixel_count;
	size_t size;
	size_t i;

	if (pixels == NULL || width <= 0 || height <= 0)
		return NULL;
	pixel_count = (size_t)width * (size_t)height;
	if (pixel_count / (size_t)width != (size_t)height)
		return NULL;
	size = pixel_count * 4;
	if (size / 4 != pixel_count || size > XBOX_GL_BGRA_STAGING_LIMIT)
		return NULL;
	converted = (unsigned char *)malloc(size);
	if (converted == NULL)
		return NULL;
	for (i = 0; i < size; i += 4)
	{
		converted[i + 0] = source[i + 2];
		converted[i + 1] = source[i + 1];
		converted[i + 2] = source[i + 0];
		converted[i + 3] = source[i + 3];
	}
	return converted;
}

void Xbox_GLTexImage2D(xbox_gl_tex_image_2d_fn upload, GLenum target,
	GLint level, GLint internalformat, GLsizei width, GLsizei height,
	GLint border, GLenum format, GLenum type, const GLvoid *pixels)
{
	unsigned char *converted;

	if (upload == NULL)
		return;
	if (format != GL_BGRA || type != GL_UNSIGNED_BYTE)
	{
		Xbox_GLUploadImage2D(upload, target, level, internalformat,
			width, height, border,
			format, type, pixels);
		return;
	}
	if (pixels == NULL)
	{
		Xbox_GLUploadImage2D(upload, target, level, internalformat,
			width, height, border,
			GL_RGBA, type, NULL);
		return;
	}
	converted = Xbox_GLConvertBGRA(pixels, width, height);
	if (converted == NULL)
	{
		/* Preserve GL_BGRA so pbGL reports GL_INVALID_OPERATION. */
		Xbox_GLUploadImage2D(upload, target, level, internalformat,
			width, height, border,
			format, type, pixels);
		return;
	}
	Xbox_GLUploadImage2D(upload, target, level, internalformat,
		width, height, border,
		GL_RGBA, type, converted);
	free(converted);
}

void Xbox_GLTexSubImage2D(xbox_gl_tex_sub_image_2d_fn upload, GLenum target,
	GLint level, GLint xoffset, GLint yoffset, GLsizei width, GLsizei height,
	GLenum format, GLenum type, const GLvoid *pixels)
{
	unsigned char *converted;

	if (upload == NULL)
		return;
	if (format != GL_BGRA || type != GL_UNSIGNED_BYTE || pixels == NULL)
	{
		Xbox_GLUploadSubImage2D(upload, target, level, xoffset, yoffset,
			width, height,
			format, type, pixels);
		return;
	}
	converted = Xbox_GLConvertBGRA(pixels, width, height);
	if (converted == NULL)
	{
		Xbox_GLUploadSubImage2D(upload, target, level, xoffset, yoffset,
			width, height,
			format, type, pixels);
		return;
	}
	Xbox_GLUploadSubImage2D(upload, target, level, xoffset, yoffset,
		width, height,
		GL_RGBA, type, converted);
	free(converted);
}
