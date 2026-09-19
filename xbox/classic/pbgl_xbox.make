# The pinned pbGL library with one hash-checked Xbox texture-table overlay.
# All other pbGL translation units stay at their immutable dependency revision.
PBGL_VERSION := 0.1
PBGL_GL_VERSION := 1.2
PBGL_LIB := $(CLASSIC_PORT_DIR)/build/libpbgl-xbox.lib
PBGL_SRCS := $(filter-out $(PBGL_DIR)/src/texture.c,$(wildcard $(PBGL_DIR)/src/*.c)) \
	$(PATCHED_PBGL_TEXTURE)
PBGL_CFLAGS := -I$(PBGL_DIR)/include -I$(PBGL_DIR)/src
ifeq ($(DEBUG),y)
PBGL_CFLAGS += -DPBGL_DEBUG
endif
PBGL_CFLAGS += -DXBOX -DPBGL_VERSION=$(PBGL_VERSION) -DPBGL_GL_VERSION=$(PBGL_GL_VERSION)
PBGL_OBJS := $(PBGL_SRCS:.c=.obj)
$(PBGL_LIB): CFLAGS += $(PBGL_CFLAGS)
$(PBGL_LIB): $(PBGL_OBJS)

.PHONY: clean-pbgl
clean-pbgl:
	$(VE)rm -f $(PBGL_OBJS) $(PBGL_LIB)
clean: clean-pbgl
