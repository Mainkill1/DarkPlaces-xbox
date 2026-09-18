/* Durable bring-up trace.  Every write is flushed so the last completed
 * boundary survives a renderer hang or fatal error. */

#include <stdarg.h>
#include <stdio.h>

#include "include/xbox_boot_trace.h"

static FILE *xbox_boot_trace;
static unsigned int xbox_boot_trace_sequence;

int Xbox_BootTraceOpen(const char *path)
{
	Xbox_BootTraceClose();
	xbox_boot_trace = fopen(path, "wb");
	if (!xbox_boot_trace)
		return -1;
	setvbuf(xbox_boot_trace, NULL, _IONBF, 0);
	xbox_boot_trace_sequence = 0;
	Xbox_BootTraceMark("boot trace opened");
	return 0;
}

void Xbox_BootTraceMark(const char *format, ...)
{
	va_list arguments;

	if (!xbox_boot_trace || !format)
		return;
	fprintf(xbox_boot_trace, "%04u ", ++xbox_boot_trace_sequence);
	va_start(arguments, format);
	vfprintf(xbox_boot_trace, format, arguments);
	va_end(arguments);
	fputc('\n', xbox_boot_trace);
	fflush(xbox_boot_trace);
}

void Xbox_BootTraceWrite(const char *text)
{
	if (!xbox_boot_trace || !text)
		return;
	fputs(text, xbox_boot_trace);
	fflush(xbox_boot_trace);
}

void Xbox_BootTraceClose(void)
{
	if (!xbox_boot_trace)
		return;
	fflush(xbox_boot_trace);
	fclose(xbox_boot_trace);
	xbox_boot_trace = NULL;
}
