/* SPDX-License-Identifier: GPL-2.0-or-later
 * nxdk's Z_SOLO build requires explicit stream allocators. Use these only with
 * that SDK build; leaving zalloc NULL would reject every inflateInit2 call.
 */
#ifndef DP_XBOX_ZALLOC_H
#define DP_XBOX_ZALLOC_H
#include <stdint.h>
#include <stdlib.h>
#include <zlib.h>
static voidpf DP_XboxZAlloc(voidpf opaque, uInt count, uInt bytes)
{
    (void)opaque;
    if (bytes && (size_t)count > SIZE_MAX / (size_t)bytes) return NULL;
    return calloc((size_t)count, (size_t)bytes);
}
static void DP_XboxZFree(voidpf opaque, voidpf memory) { (void)opaque; free(memory); }
static int DP_XboxInflateInit2(z_stream *stream, int bits)
{
    stream->zalloc = DP_XboxZAlloc;
    stream->zfree = DP_XboxZFree;
    stream->opaque = NULL;
    return inflateInit2_(stream, bits, ZLIB_VERSION, sizeof(*stream));
}
static int DP_XboxDeflateInit2(z_stream *stream, int level, int method, int bits,
                             int memory_level, int strategy)
{
    stream->zalloc = DP_XboxZAlloc;
    stream->zfree = DP_XboxZFree;
    stream->opaque = NULL;
    return deflateInit2_(stream, level, method, bits, memory_level, strategy,
                         ZLIB_VERSION, sizeof(*stream));
}
#endif
