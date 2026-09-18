#ifndef XBOX_CLASSIC_BOOT_TRACE_H
#define XBOX_CLASSIC_BOOT_TRACE_H

int Xbox_BootTraceOpen(const char *path);
void Xbox_BootTraceMark(const char *format, ...) __attribute__((format(printf, 1, 2)));
void Xbox_BootTraceWrite(const char *text);
void Xbox_BootTraceClose(void);

#endif
