# Playable Nexuiz Classic target for the Original Xbox.
#
# This target deliberately builds a DarkPlaces revision contemporary with
# Nexuiz 2.5.2 because that engine still owns the GL1.1/GL1.3 fixed-function
# renderer. pbGL maps that path to PBKit/NV2A; this avoids pretending that the
# modern GL3/GLES2 renderer can execute on NV2A.

.DEFAULT_GOAL := all

ROOT_DIR := $(abspath $(CURDIR)/../..)
include $(CURDIR)/versions.mk

NXDK_DIR ?= $(abspath $(ROOT_DIR)/../nxdk)
ENGINE_DIR ?= $(abspath $(ROOT_DIR)/../darkplaces-classic)
PBGL_DIR ?= $(abspath $(ROOT_DIR)/../pbgl)
OGG_DIR ?= $(abspath $(ROOT_DIR)/../ogg)
VORBIS_DIR ?= $(abspath $(ROOT_DIR)/../vorbis)
PYTHON ?= python3

export NXDK_DIR
export PATH := $(NXDK_DIR)/bin:$(PATH)

NXDK_SDL := y
XBE_TITLE := Nexuiz\ Xbox
OUTPUT_DIR ?= $(CURDIR)/build/disc
GEN_XISO ?= $(CURDIR)/nexuiz-xbox.iso

CLASSIC_PORT_DIR := $(CURDIR)
CLASSIC_INCLUDE_DIR := $(CLASSIC_PORT_DIR)/include

# Mirrors the Nexuiz-era OBJ_COMMON list. sys_shared.c is deliberately replaced
# by sys_xbox.c because its desktop dlopen/process implementation is not valid
# on the console.
ENGINE_COMMON := \
	cap_avi.c cap_ogg.c cd_shared.c \
	cl_collision.c cl_demo.c cl_dyntexture.c cl_gecko.c cl_input.c cl_main.c \
	cl_parse.c cl_particles.c cl_screen.c cl_video.c clvm_cmds.c cmd.c \
	collision.c common.c console.c csprogs.c curves.c cvar.c dpvsimpledecode.c \
	filematch.c fractalnoise.c gl_backend.c gl_draw.c \
	gl_rsurf.c gl_textures.c hmac.c host.c host_cmd.c image.c jpeg.c keys.c \
	lhnet.c libcurl.c mathlib.c matrixlib.c mdfour.c menu.c meshqueue.c \
	model_alias.c model_brush.c model_shared.c model_sprite.c mvm_cmds.c \
	netconn.c palette.c polygon.c portals.c protocol.c prvm_cmds.c prvm_edict.c \
	prvm_exec.c r_explosion.c r_lerpanim.c r_lightning.c r_modules.c \
	r_shadow.c r_sky.c r_sprites.c sbar.c sv_demo.c sv_main.c sv_move.c \
	sv_phys.c sv_user.c svbsp.c svvm_cmds.c vid_shared.c view.c wad.c world.c zone.c

ENGINE_SOUND := snd_main.c snd_mem.c snd_mix.c snd_ogg.c snd_wav.c snd_modplug.c
PATCHED_FS := $(CLASSIC_PORT_DIR)/build/generated/fs_xbox.c
PATCHED_GL_RMAIN := $(CLASSIC_PORT_DIR)/build/generated/gl_rmain_xbox.c
MEMORY_HEADER_DIR := $(CLASSIC_PORT_DIR)/build/generated/memory
PATCHED_QUAKEDEF := $(MEMORY_HEADER_DIR)/quakedef_xbox.h
PATCHED_NETCONN := $(MEMORY_HEADER_DIR)/netconn_xbox.h
ENGINE_SRCS := $(addprefix $(ENGINE_DIR)/,$(ENGINE_COMMON) $(ENGINE_SOUND) builddate.c cd_null.c) \
	$(PATCHED_FS) $(PATCHED_GL_RMAIN)

# Do not wildcard third-party codec directories. The release lock pins exact
# source revisions and the Xbox executable carries only the library translation
# units needed by libvorbisfile. In particular, vorbisenc.c and utility/test
# sources are not part of the game executable.
OGG_SRCS := \
	$(OGG_DIR)/src/bitwise.c \
	$(OGG_DIR)/src/framing.c

VORBIS_CORE_NAMES := \
	mdct.c smallft.c block.c envelope.c window.c lsp.c lpc.c analysis.c \
	synthesis.c psy.c info.c floor1.c floor0.c res0.c mapping0.c registry.c \
	codebook.c sharedbook.c lookup.c bitrate.c
VORBIS_SRCS := $(addprefix $(VORBIS_DIR)/lib/,$(VORBIS_CORE_NAMES)) \
	$(VORBIS_DIR)/lib/vorbisfile.c

PORT_SRCS := \
	$(CLASSIC_PORT_DIR)/sys_xbox.c \
	$(CLASSIC_PORT_DIR)/memory_policy_xbox.c \
	$(CLASSIC_PORT_DIR)/memory_profile_xbox.c \
	$(CLASSIC_PORT_DIR)/vid_xbox.c \
	$(CLASSIC_PORT_DIR)/gl_compat.c \
	$(CLASSIC_PORT_DIR)/gl_upload_xbox.c \
	$(CLASSIC_PORT_DIR)/gl_bootstrap_xbox.c \
	$(CLASSIC_PORT_DIR)/zlib_xbox.c \
	$(CLASSIC_PORT_DIR)/png_decode_xbox.c \
	$(CLASSIC_PORT_DIR)/image_png_xbox.c \
	$(CLASSIC_PORT_DIR)/boot_trace_xbox.c \
	$(CLASSIC_PORT_DIR)/storage_xbox.c \
	$(CLASSIC_PORT_DIR)/path_xbox.c \
	$(CLASSIC_PORT_DIR)/network_gate_xbox.c \
	$(CLASSIC_PORT_DIR)/posix_io.c \
	$(CLASSIC_PORT_DIR)/dirent_xbox.c \
	$(CLASSIC_PORT_DIR)/stat_xbox.c \
	$(CLASSIC_PORT_DIR)/crt_xbox.c \
	$(CLASSIC_PORT_DIR)/snd_xbox.c \
	$(CLASSIC_PORT_DIR)/net_xbox.c \
	$(ROOT_DIR)/xbox/attract_policy.c

SRCS := $(PORT_SRCS) $(ENGINE_SRCS) $(OGG_SRCS) $(VORBIS_SRCS)

DP_CLASSIC_CFLAGS := -O2 -fno-strict-aliasing -ffunction-sections -fdata-sections
DP_CLASSIC_CFLAGS += -I$(ENGINE_DIR) -I$(CLASSIC_INCLUDE_DIR) -I$(ROOT_DIR)
DP_CLASSIC_CFLAGS += -include $(CLASSIC_INCLUDE_DIR)/xbox_posix_io.h
DP_CLASSIC_CFLAGS += -I$(OGG_DIR)/include -I$(VORBIS_DIR)/include -I$(VORBIS_DIR)/lib
DP_CLASSIC_CFLAGS += -I$(PBGL_DIR)/include
DP_CLASSIC_CFLAGS += -DDP_PLATFORM_XBOX=1 -DXBOX=1 -DCONFIG_MENU=1
# The nxdk Clang target advertises MSVC ABI compatibility through _MSC_VER,
# but the console runtime is PDCLib rather than Microsoft's CRT.  The pinned
# engine otherwise selects unsupported secure-CRT calls such as _sopen_s and
# the incompatible MSVC forms of localtime_s/gmtime_s.
DP_CLASSIC_CFLAGS += -U_MSC_VER
DP_CLASSIC_CFLAGS += -DLINK_TO_LIBJPEG=1
DP_CLASSIC_CFLAGS += -D_fseeki64=fseek -D_ftelli64=ftell
DP_CLASSIC_CFLAGS += -Dstrcasecmp=_stricmp -Dstrncasecmp=_strnicmp
DP_CLASSIC_CFLAGS += -DSVNREVISION=\"xbox-nexuiz-252\" -DBUILDTYPE=release
DP_CLASSIC_CFLAGS += -Wno-unused-parameter -Wno-sign-compare -Wno-deprecated-declarations

APP_OBJS := $(SRCS:.c=.obj)
ENGINE_OBJS := $(ENGINE_SRCS:.c=.obj)
MEMORY_PROFILE_OBJS := $(filter-out $(ENGINE_DIR)/builddate.obj,$(ENGINE_OBJS)) \
	$(CLASSIC_PORT_DIR)/vid_xbox.obj
$(APP_OBJS): CFLAGS += $(DP_CLASSIC_CFLAGS)
$(MEMORY_PROFILE_OBJS): CFLAGS += -include $(PATCHED_QUAKEDEF)
$(MEMORY_PROFILE_OBJS): $(PATCHED_QUAKEDEF) $(PATCHED_NETCONN)

# The executable is intentionally large-stack while the port is being brought
# up. It remains part of the 64 MiB budget and can be tightened after measured
# high-water data exists.
LDFLAGS += -stack:1048576 -opt:ref

include $(NXDK_DIR)/Makefile
include $(PBGL_DIR)/config_pbgl.make

# pbGL is the NV2A fixed-function implementation used by the historical GL13
# path. The engine never opens a desktop OpenGL context.
main.exe: $(PBGL_LIB)

# Keep compiler flags for dependency sources local to this target.
$(OGG_SRCS:.c=.obj): CFLAGS += -DOGG_STATIC
$(VORBIS_SRCS:.c=.obj): CFLAGS += -DOGG_STATIC -Dalloca=__builtin_alloca

$(PATCHED_FS): $(ENGINE_DIR)/fs.c $(ROOT_DIR)/tools/xbox/patch_classic_fs.py
	@mkdir -p "$(dir $@)"
	@$(PYTHON) "$(ROOT_DIR)/tools/xbox/patch_classic_fs.py" "$<" "$@"

$(PATCHED_GL_RMAIN): $(ENGINE_DIR)/gl_rmain.c $(ROOT_DIR)/tools/xbox/patch_classic_skin_layers.py
	@mkdir -p "$(dir $@)"
	@$(PYTHON) "$(ROOT_DIR)/tools/xbox/patch_classic_skin_layers.py" "$<" "$@"

$(PATCHED_QUAKEDEF): $(ENGINE_DIR)/quakedef.h $(ENGINE_DIR)/netconn.h $(ROOT_DIR)/tools/xbox/patch_classic_memory_headers.py
	@mkdir -p "$(MEMORY_HEADER_DIR)"
	@$(PYTHON) "$(ROOT_DIR)/tools/xbox/patch_classic_memory_headers.py" \
		"$(ENGINE_DIR)/quakedef.h" "$(ENGINE_DIR)/netconn.h" "$(MEMORY_HEADER_DIR)"

# The generator writes both headers atomically. Keep the second output
# recoverable when it alone is removed without requiring GNU make grouped
# targets (introduced in 4.3).
$(PATCHED_NETCONN): $(PATCHED_QUAKEDEF)
	@test -f "$@" || { \
		mkdir -p "$(MEMORY_HEADER_DIR)"; \
		$(PYTHON) "$(ROOT_DIR)/tools/xbox/patch_classic_memory_headers.py" \
			"$(ENGINE_DIR)/quakedef.h" "$(ENGINE_DIR)/netconn.h" "$(MEMORY_HEADER_DIR)"; \
	}

.PHONY: print-pins
print-pins:
	@echo "DarkPlaces $(DP_CLASSIC_REV)"
	@echo "pbGL       $(PBGL_REV)"
	@echo "libogg     $(OGG_REV)"
	@echo "libvorbis  $(VORBIS_REV)"
	@echo "Nexuiz SHA $(NEXUIZ_252_SHA256)"
	@echo "Nexuiz MD5 $(NEXUIZ_252_MD5)"
