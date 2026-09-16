/* SPDX-License-Identifier: GPL-2.0-or-later
 * Option B excludes Internet transfer services. A refused transfer never calls
 * its callback, because callers already own the synchronous failure path.
 */
#include "quakedef.h"
#include "libcurl.h"
void Curl_Frame(void) { }
bool Curl_Select(int timeout_ms) { (void)timeout_ms; return false; }
qbool Curl_Running(void) { return false; }
qbool Curl_Available(void) { return false; }
void Curl_Init(void) { Con_Print("Xbox: automatic external downloads disabled\n"); }
void Curl_Init_Commands(void) { }
void Curl_Shutdown(void) { }
void Curl_CancelAll(void) { }
void Curl_Clear_forthismap(void) { }
qbool Curl_Have_forthismap(void) { return false; }
void Curl_Register_predownload(void) { }
void Curl_ClearRequirements(void) { }
void Curl_RequireFile(const char *filename) { (void)filename; }
void Curl_SendRequirements(void) { }
void Curl_Cancel_ToMemory(curl_callback_t callback, void *data) { (void)callback; (void)data; }
qbool Curl_Begin_ToFile(const char *url, double speed, const char *name, int loadtype, qbool map)
{
    (void)url; (void)speed; (void)name; (void)loadtype; (void)map;
    return false;
}
qbool Curl_Begin_ToMemory(const char *url, double speed, unsigned char *buffer,
    size_t size, curl_callback_t callback, void *data)
{
    (void)url; (void)speed; (void)buffer; (void)size; (void)callback; (void)data;
    return false;
}
qbool Curl_Begin_ToMemory_POST(const char *url, const char *headers, double speed,
    const char *content_type, const unsigned char *post, size_t postsize,
    unsigned char *buffer, size_t size, curl_callback_t callback, void *data)
{
    (void)headers; (void)content_type; (void)post; (void)postsize;
    return Curl_Begin_ToMemory(url, speed, buffer, size, callback, data);
}
Curl_downloadinfo_t *Curl_GetDownloadInfo(int *count, const char **info, char *buffer, size_t size)
{
    if (count) *count = 0;
    if (info) *info = "External downloads disabled on Xbox";
    if (buffer && size) buffer[0] = '\0';
    return NULL;
}
