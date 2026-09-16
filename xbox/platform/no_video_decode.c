/* SPDX-License-Identifier: GPL-2.0-or-later
 * Optional libavw decoder is not a game renderer and is not linked on Xbox.
 * Refuse this optional codec explicitly; built-in video decoders remain owned
 * by cl_video.c. Never return a fabricated successful stream.
 */
#include "cl_video_libavw.h"
void libavw_close(void *stream) { (void)stream; }
void *LibAvW_OpenVideo(clvideo_t *video, char *filename, const char **error)
{
    (void)video; (void)filename;
    if (error) *error = "libavw video decoding unavailable on Xbox";
    return NULL;
}
qbool LibAvW_OpenLibrary(void) { return false; }
void LibAvW_CloseLibrary(void) { }
