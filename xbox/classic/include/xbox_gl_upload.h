#ifndef XBOX_GL_UPLOAD_H
#define XBOX_GL_UPLOAD_H

#include <GL/gl.h>
#include <GL/glext.h>

typedef void (*xbox_gl_tex_image_2d_fn)(GLenum target, GLint level,
	GLint internalformat, GLsizei width, GLsizei height, GLint border,
	GLenum format, GLenum type, const GLvoid *pixels);
typedef void (*xbox_gl_tex_sub_image_2d_fn)(GLenum target, GLint level,
	GLint xoffset, GLint yoffset, GLsizei width, GLsizei height,
	GLenum format, GLenum type, const GLvoid *pixels);

void Xbox_GLTexImage2D(xbox_gl_tex_image_2d_fn upload, GLenum target,
	GLint level, GLint internalformat, GLsizei width, GLsizei height,
	GLint border, GLenum format, GLenum type, const GLvoid *pixels);
void Xbox_GLTexSubImage2D(xbox_gl_tex_sub_image_2d_fn upload, GLenum target,
	GLint level, GLint xoffset, GLint yoffset, GLsizei width, GLsizei height,
	GLenum format, GLenum type, const GLvoid *pixels);

#endif
