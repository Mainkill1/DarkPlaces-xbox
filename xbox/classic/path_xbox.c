/* Canonical DOS-style paths for nxdk's Win32-compatible file boundary. */

#include <errno.h>
#include <string.h>

#include "include/xbox_path.h"

int Xbox_NormalizePath(const char *source, char *destination, size_t capacity)
{
	size_t length;
	size_t read_index;
	size_t write_index = 0;
	int component_start = 1;

	if (!source || !destination || !capacity)
	{
		errno = EINVAL;
		return -1;
	}
	length = strlen(source);
	if (!length)
	{
		errno = EINVAL;
		return -1;
	}
	if (length >= capacity)
	{
		errno = ENAMETOOLONG;
		return -1;
	}

	for (read_index = 0; read_index < length;)
	{
		char character = source[read_index];
		char next = read_index + 1 < length ? source[read_index + 1] : '\0';

		if (component_start && character == '.' &&
		    (next == '/' || next == '\\' || next == '\0'))
		{
			++read_index;
			if (read_index < length &&
			    (source[read_index] == '/' || source[read_index] == '\\'))
				++read_index;
			continue;
		}

		if (character == '/')
			character = '\\';
		destination[write_index++] = character;
		component_start = character == '\\';
		++read_index;
	}
	destination[write_index] = '\0';
	return 0;
}
