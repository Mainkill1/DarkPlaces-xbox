#ifndef XBOX_GL_STATE_H
#define XBOX_GL_STATE_H

#include <GL/gl.h>
#include <GL/glext.h>

typedef void (*xbox_gl_active_texture_fn)(GLenum unit);
typedef void (*xbox_gl_bind_texture_fn)(GLenum target, GLuint texture);
typedef void (*xbox_gl_get_integer_fn)(GLenum pname, GLint *params);
typedef void (*xbox_gl_get_boolean_fn)(GLenum pname, GLboolean *params);
typedef GLboolean (*xbox_gl_is_enabled_fn)(GLenum feature);

void Xbox_GLStateReset(void);
void Xbox_GLActiveTexture(xbox_gl_active_texture_fn active, GLenum unit);
void Xbox_GLBindTexture(xbox_gl_bind_texture_fn bind, GLenum target,
	GLuint texture);
void Xbox_GLGetIntegerv(xbox_gl_get_integer_fn query, GLenum pname,
	GLint *params);
GLboolean Xbox_GLIsEnabled(xbox_gl_is_enabled_fn query,
	xbox_gl_get_boolean_fn query_boolean, GLenum feature);

#endif
