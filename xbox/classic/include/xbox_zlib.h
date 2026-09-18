#ifndef XBOX_CLASSIC_ZLIB_H
#define XBOX_CLASSIC_ZLIB_H

#include <zlib.h>

int ZEXPORT Xbox_ZlibInflateInit2_(z_streamp stream, int window_bits,
	const char *version, int stream_size);
int ZEXPORT Xbox_ZlibDeflateInit2_(z_streamp stream, int level, int method,
	int window_bits, int memory_level, int strategy, const char *version,
	int stream_size);

#endif
