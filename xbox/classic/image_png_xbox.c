#include "quakedef.h"
#include "image_png.h"
#include "xbox_png.h"

extern int image_width;
extern int image_height;

static void *Xbox_PngAllocate(void *opaque, size_t size)
{
	(void)opaque;
	return Mem_Alloc(tempmempool, size);
}

static void Xbox_PngRelease(void *opaque, void *address)
{
	(void)opaque;
	if (address != NULL)
		Mem_Free(address);
}

qboolean PNG_OpenLibrary(void)
{
	/* The Xbox target links the pinned libpng and uses its typed API directly. */
	return true;
}

void PNG_CloseLibrary(void)
{
}

unsigned char *PNG_LoadImage_BGRA(const unsigned char *raw, int filesize)
{
	xbox_png_image_t image;
	char error[160];

	if (filesize < 0)
		return NULL;
	if (!Xbox_PngDecodeBGRA(raw, (size_t)filesize, Xbox_PngAllocate,
		Xbox_PngRelease, NULL, &image, error, sizeof(error)))
	{
		Con_Printf("PNG_LoadImage_BGRA: %s\n", error);
		return NULL;
	}
	image_width = (int)image.width;
	image_height = (int)image.height;
	return image.pixels;
}
