/* Establish the one GL dispatch entry required before DarkPlaces can run its
 * normal extension resolver.  pbGL is statically linked, but the historical
 * engine still expects qglGetString to be populated explicitly. */

#include <stdint.h>
#include "glquake.h"

#include "include/xbox_boot_trace.h"
#include "include/xbox_gl_bootstrap.h"

extern void *GL_GetProcAddress(const char *name);

int Xbox_GLBootstrap(int pbgl_result)
{
	const GLubyte *renderer;
	const GLubyte *vendor;
	const GLubyte *version;
	const GLubyte *extensions;

	if (pbgl_result != 0)
	{
		Xbox_BootTraceMark("GL bootstrap rejected pbgl result %d", pbgl_result);
		return XBOX_GL_BOOTSTRAP_PBGL_FAILED;
	}

	qglGetString = (const GLubyte* (GLAPIENTRY *)(GLenum))GL_GetProcAddress("glGetString");
	Xbox_BootTraceMark("qglGetString resolved %p", (void *)(uintptr_t)qglGetString);
	if (!qglGetString)
		return XBOX_GL_BOOTSTRAP_RESOLVE_FAILED;

	renderer = qglGetString(GL_RENDERER);
	vendor = qglGetString(GL_VENDOR);
	version = qglGetString(GL_VERSION);
	extensions = qglGetString(GL_EXTENSIONS);
	if (!renderer || !vendor || !version || !extensions)
	{
		Xbox_BootTraceMark("GL identity query failed renderer=%p vendor=%p version=%p extensions=%p",
			(void *)renderer, (void *)vendor, (void *)version, (void *)extensions);
		return XBOX_GL_BOOTSTRAP_IDENTITY_FAILED;
	}

	Xbox_BootTraceMark("GL identity renderer=%s vendor=%s version=%s",
		(const char *)renderer, (const char *)vendor, (const char *)version);
	return XBOX_GL_BOOTSTRAP_OK;
}
