#include <string.h>

#include "xbox_gl_state.h"

#define XBOX_GL_TEXTURE_UNITS 4

static unsigned int active_texture_unit;
static GLint bound_texture_2d[XBOX_GL_TEXTURE_UNITS];

void Xbox_GLStateReset(void)
{
	active_texture_unit = 0;
	memset(bound_texture_2d, 0, sizeof(bound_texture_2d));
}

void Xbox_GLActiveTexture(xbox_gl_active_texture_fn active, GLenum unit)
{
	if (!active)
		return;
	active(unit);
	if (unit >= GL_TEXTURE0
		&& unit < GL_TEXTURE0 + XBOX_GL_TEXTURE_UNITS)
		active_texture_unit = (unsigned int)(unit - GL_TEXTURE0);
}

void Xbox_GLBindTexture(xbox_gl_bind_texture_fn bind, GLenum target,
	GLuint texture)
{
	if (!bind)
		return;
	bind(target, texture);
	if (target == GL_TEXTURE_2D)
		bound_texture_2d[active_texture_unit] = (GLint)texture;
}

void Xbox_GLGetIntegerv(xbox_gl_get_integer_fn query, GLenum pname,
	GLint *params)
{
	if (!params)
		return;
	if (pname == GL_TEXTURE_BINDING_2D)
	{
		*params = bound_texture_2d[active_texture_unit];
		return;
	}
	if (query)
		query(pname, params);
}

GLboolean Xbox_GLIsEnabled(xbox_gl_is_enabled_fn query,
	xbox_gl_get_boolean_fn query_boolean, GLenum feature)
{
	GLboolean enabled = GL_FALSE;
	switch (feature)
	{
	case GL_VERTEX_ARRAY:
	case GL_NORMAL_ARRAY:
	case GL_COLOR_ARRAY:
	case GL_TEXTURE_COORD_ARRAY:
#ifdef GL_SECONDARY_COLOR_ARRAY
	case GL_SECONDARY_COLOR_ARRAY:
#endif
#ifdef GL_FOG_COORD_ARRAY
	case GL_FOG_COORD_ARRAY:
#endif
		if (query_boolean)
			query_boolean(feature, &enabled);
		return enabled;
	default:
		return query ? query(feature) : GL_FALSE;
	}
}
