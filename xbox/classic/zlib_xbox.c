/* Adapt the historical engine's hosted-zlib expectations to nxdk's Z_SOLO
 * build, which deliberately requires the caller to provide allocators. */

#include <stdint.h>
#include <stdlib.h>

#include "include/xbox_zlib.h"

static voidpf Xbox_ZlibAlloc(voidpf opaque, uInt items, uInt size)
{
	size_t bytes;
	(void)opaque;
	if (items != 0 && (size_t)size > SIZE_MAX / (size_t)items)
		return Z_NULL;
	bytes = (size_t)items * (size_t)size;
	return bytes ? calloc(1, bytes) : Z_NULL;
}

static void Xbox_ZlibFree(voidpf opaque, voidpf address)
{
	(void)opaque;
	free(address);
}

static int Xbox_ZlibPrepareStream(z_streamp stream)
{
	if (!stream)
		return Z_STREAM_ERROR;
	if ((stream->zalloc == Z_NULL) != (stream->zfree == Z_NULL))
		return Z_STREAM_ERROR;
	if (stream->zalloc == Z_NULL)
	{
		stream->zalloc = Xbox_ZlibAlloc;
		stream->zfree = Xbox_ZlibFree;
		stream->opaque = Z_NULL;
	}
	return Z_OK;
}

int ZEXPORT Xbox_ZlibInflateInit2_(z_streamp stream, int window_bits,
	const char *version, int stream_size)
{
	int result = Xbox_ZlibPrepareStream(stream);
	if (result != Z_OK)
		return result;
	return inflateInit2_(stream, window_bits, version, stream_size);
}

int ZEXPORT Xbox_ZlibDeflateInit2_(z_streamp stream, int level, int method,
	int window_bits, int memory_level, int strategy, const char *version,
	int stream_size)
{
	int result = Xbox_ZlibPrepareStream(stream);
	if (result != Z_OK)
		return result;
	return deflateInit2_(stream, level, method, window_bits, memory_level,
		strategy, version, stream_size);
}
