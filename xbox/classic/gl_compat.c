#define GL_GLEXT_PROTOTYPES
#include <string.h>
#include <pbgl.h>
#include <GL/gl.h>
#include <GL/glext.h>

#include "quakedef.h"

/*
 * DarkPlaces 2009 resolves GL entry points at runtime. pbGL is statically
 * linked, so expose the required GL1.1 functions through the same resolver.
 * Missing optional extensions intentionally resolve to NULL and are disabled
 * by VID_CheckExtensions().
 */

static GLdouble clip_planes[6][4];

static void Xbox_glDrawBuffer(GLenum mode) { (void)mode; }
static void Xbox_glReadBuffer(GLenum mode) { (void)mode; }

static void Xbox_glGetDoublev(GLenum pname, GLdouble *params)
{
	GLfloat f[16];
	int i, count = 1;
	memset(f, 0, sizeof(f));
	glGetFloatv(pname, f);
	if (pname == GL_MODELVIEW_MATRIX || pname == GL_PROJECTION_MATRIX || pname == GL_TEXTURE_MATRIX)
		count = 16;
	else if (pname == GL_VIEWPORT)
		count = 4;
	for (i = 0; i < count; ++i)
		params[i] = (GLdouble)f[i];
}

static void Xbox_glPixelStoref(GLenum pname, GLfloat value)
{
	glPixelStorei(pname, (GLint)value);
}

static void Xbox_glTexCoord1f(GLfloat s)
{
	glTexCoord4f(s, 0.f, 0.f, 1.f);
}

static void Xbox_glMultiTexCoord1f(GLenum unit, GLfloat s)
{
	glMultiTexCoord4f(unit, s, 0.f, 0.f, 1.f);
}

static void Xbox_glTexImage1D(GLenum target, GLint level, GLint internalformat,
	GLsizei width, GLint border, GLenum format, GLenum type, const GLvoid *pixels)
{
	(void)target;
	glTexImage2D(GL_TEXTURE_2D, level, internalformat, width, 1, border, format, type, pixels);
}

static void Xbox_glTexSubImage1D(GLenum target, GLint level, GLint xoffset,
	GLint x, GLint y, GLsizei width, GLenum format, GLenum type, const GLvoid *pixels)
{
	(void)target; (void)x; (void)y;
	glTexSubImage2D(GL_TEXTURE_2D, level, xoffset, 0, width, 1, format, type, pixels);
}

static void Xbox_glCopyTexImage1D(GLenum target, GLint level, GLenum internalformat,
	GLint x, GLint y, GLsizei width, GLint border)
{
	(void)target;
	glCopyTexImage2D(GL_TEXTURE_2D, level, internalformat, x, y, width, 1, border);
}

static void Xbox_glCopyTexSubImage1D(GLenum target, GLint level, GLint xoffset,
	GLint x, GLint y, GLsizei width)
{
	(void)target;
	glCopyTexSubImage2D(GL_TEXTURE_2D, level, xoffset, 0, x, y, width, 1);
}

static void Xbox_glPolygonStipple(const GLubyte *mask) { (void)mask; }

static void Xbox_glClipPlane(GLenum plane, const GLdouble *equation)
{
	int n = (int)plane - (int)GL_CLIP_PLANE0;
	if (n >= 0 && n < 6 && equation)
		memcpy(clip_planes[n], equation, sizeof(clip_planes[n]));
}

static void Xbox_glGetClipPlane(GLenum plane, GLdouble *equation)
{
	int n = (int)plane - (int)GL_CLIP_PLANE0;
	if (n >= 0 && n < 6 && equation)
		memcpy(equation, clip_planes[n], sizeof(clip_planes[n]));
}

#define MAP_GL(name) if (!strcmp(name_string, #name)) return (void *)(name)

void *GL_GetProcAddress(const char *name_string)
{
	if (!name_string)
		return NULL;

	MAP_GL(glClearColor); MAP_GL(glClear); MAP_GL(glAlphaFunc); MAP_GL(glBlendFunc);
	MAP_GL(glCullFace); MAP_GL(glEnable); MAP_GL(glDisable); MAP_GL(glIsEnabled);
	MAP_GL(glEnableClientState); MAP_GL(glDisableClientState); MAP_GL(glGetBooleanv);
	MAP_GL(glGetFloatv); MAP_GL(glGetIntegerv); MAP_GL(glGetError); MAP_GL(glGetString);
	MAP_GL(glFinish); MAP_GL(glFlush); MAP_GL(glClearDepth); MAP_GL(glDepthFunc);
	MAP_GL(glDepthMask); MAP_GL(glDepthRange); MAP_GL(glDrawElements); MAP_GL(glColorMask);
	MAP_GL(glVertexPointer); MAP_GL(glNormalPointer); MAP_GL(glColorPointer);
	MAP_GL(glTexCoordPointer); MAP_GL(glArrayElement); MAP_GL(glColor4f);
	MAP_GL(glTexCoord2f); MAP_GL(glTexCoord3f); MAP_GL(glTexCoord4f);
	MAP_GL(glVertex2f); MAP_GL(glVertex3f); MAP_GL(glBegin); MAP_GL(glEnd);
	MAP_GL(glLineWidth); MAP_GL(glPointSize); MAP_GL(glMatrixMode); MAP_GL(glOrtho);
	MAP_GL(glFrustum); MAP_GL(glViewport); MAP_GL(glPushMatrix); MAP_GL(glPopMatrix);
	MAP_GL(glLoadIdentity); MAP_GL(glLoadMatrixd); MAP_GL(glLoadMatrixf);
	MAP_GL(glMultMatrixd); MAP_GL(glMultMatrixf); MAP_GL(glRotated); MAP_GL(glRotatef);
	MAP_GL(glScaled); MAP_GL(glScalef); MAP_GL(glTranslated); MAP_GL(glTranslatef);
	MAP_GL(glReadPixels); MAP_GL(glStencilFunc); MAP_GL(glStencilMask); MAP_GL(glStencilOp);
	MAP_GL(glClearStencil); MAP_GL(glTexEnvf); MAP_GL(glTexEnvfv); MAP_GL(glTexEnvi);
	MAP_GL(glTexParameterf); MAP_GL(glTexParameterfv); MAP_GL(glTexParameteri); MAP_GL(glHint);
	MAP_GL(glPixelStorei); MAP_GL(glGenTextures); MAP_GL(glDeleteTextures); MAP_GL(glBindTexture);
	MAP_GL(glIsTexture); MAP_GL(glTexImage2D); MAP_GL(glTexSubImage2D);
	MAP_GL(glCopyTexImage2D); MAP_GL(glCopyTexSubImage2D); MAP_GL(glScissor);
	MAP_GL(glPolygonOffset); MAP_GL(glPolygonMode);

	if (!strcmp(name_string, "glDrawBuffer")) return (void *)Xbox_glDrawBuffer;
	if (!strcmp(name_string, "glReadBuffer")) return (void *)Xbox_glReadBuffer;
	if (!strcmp(name_string, "glGetDoublev")) return (void *)Xbox_glGetDoublev;
	if (!strcmp(name_string, "glPixelStoref")) return (void *)Xbox_glPixelStoref;
	if (!strcmp(name_string, "glTexCoord1f")) return (void *)Xbox_glTexCoord1f;
	if (!strcmp(name_string, "glTexImage1D")) return (void *)Xbox_glTexImage1D;
	if (!strcmp(name_string, "glTexSubImage1D")) return (void *)Xbox_glTexSubImage1D;
	if (!strcmp(name_string, "glCopyTexImage1D")) return (void *)Xbox_glCopyTexImage1D;
	if (!strcmp(name_string, "glCopyTexSubImage1D")) return (void *)Xbox_glCopyTexSubImage1D;
	if (!strcmp(name_string, "glPolygonStipple")) return (void *)Xbox_glPolygonStipple;
	if (!strcmp(name_string, "glClipPlane")) return (void *)Xbox_glClipPlane;
	if (!strcmp(name_string, "glGetClipPlane")) return (void *)Xbox_glGetClipPlane;

	/* pbGL exposes OpenGL 1.3 core names; DarkPlaces asks for ARB aliases. */
	if (!strcmp(name_string, "glActiveTextureARB")) return (void *)glActiveTexture;
	if (!strcmp(name_string, "glClientActiveTextureARB")) return (void *)glClientActiveTexture;
	if (!strcmp(name_string, "glMultiTexCoord1fARB")) return (void *)Xbox_glMultiTexCoord1f;
	if (!strcmp(name_string, "glMultiTexCoord2fARB")) return (void *)glMultiTexCoord2f;
	if (!strcmp(name_string, "glMultiTexCoord3fARB")) return (void *)glMultiTexCoord3f;
	if (!strcmp(name_string, "glMultiTexCoord4fARB")) return (void *)glMultiTexCoord4f;

	return NULL;
}
