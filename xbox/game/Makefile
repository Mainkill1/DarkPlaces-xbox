# Native DarkPlaces engine target. The default profile is an explicit headless
# engine bootstrap, not a renamed foundation app and not a playable release.
.DEFAULT_GOAL := all
ROOT_DIR := $(abspath $(CURDIR)/../..)
NXDK_DIR ?= $(abspath $(ROOT_DIR)/../nxdk)
PYTHON ?= python3
CONTENT_DIR ?=
export NXDK_DIR
export PATH := $(NXDK_DIR)/bin:$(PATH)

XBE_TITLE := Nexuiz\ Xbox
OUTPUT_DIR := $(CURDIR)/build/disc
GEN_XISO := $(CURDIR)/nexuiz-xbox.iso
NXDK_SDL := y
DEBUG := y
OBJ_DIR := $(CURDIR)/build/obj
IDENTITY_DIR := $(CURDIR)/build/generated

include $(CURDIR)/sources.mk
GAME_SOURCES := $(filter-out xbox/game/entry.c,$(DP_XBOX_SOURCES))
GAME_OBJECTS := $(addprefix $(OBJ_DIR)/,$(GAME_SOURCES:.c=.obj))
GAME_DEPENDENCIES := $(GAME_OBJECTS:.obj=.d)

# The no-testing delivery does not run this makefile. At build time, fail before
# compiling if toolchain or real content inputs are missing or do not match.
ifneq ($(filter clean clean-game distclean,$(MAKECMDGOALS)),)
ifneq ($(filter-out clean clean-game distclean,$(MAKECMDGOALS)),)
$(error Cleanup and build goals must be invoked separately)
endif
# Cleanup never requires installed content.
else
ifeq ($(strip $(CONTENT_DIR)),)
$(error CONTENT_DIR is required: use an output from tools/xbox/nexuiz_prepare.py --require-autoplay)
endif
SDK_OK := $(shell $(PYTHON) "$(ROOT_DIR)/tools/xbox/verify_nxdk.py" --pin-file "$(ROOT_DIR)/xbox/nxdk.version" --nxdk-dir "$(NXDK_DIR)" >&2 && printf yes)
ifneq ($(SDK_OK),yes)
$(error Pinned nxdk preflight failed)
endif
SUBMODULE_STATE := $(shell git -C "$(NXDK_DIR)" submodule status --recursive 2>/dev/null | grep -E '^[-+U]')
ifneq ($(strip $(SUBMODULE_STATE)),)
$(error nxdk submodules are not at their recorded revisions; initialize them recursively)
endif
INPUTS_OK := $(shell $(PYTHON) "$(ROOT_DIR)/tools/xbox/stage_game_disc.py" --content "$(CONTENT_DIR)" --check-only >&2 && printf yes)
ifneq ($(INPUTS_OK),yes)
$(error Real Nexuiz packaging prerequisites are missing or invalid)
endif
IDENTITY_OK := $(shell $(PYTHON) "$(ROOT_DIR)/tools/xbox/game_identity.py" --root "$(ROOT_DIR)" --nxdk "$(NXDK_DIR)" --output "$(IDENTITY_DIR)" >&2 && printf yes)
ifneq ($(IDENTITY_OK),yes)
$(error Could not produce native build identity)
endif
endif

# Do not use nxdk's default SRCS-to-adjacent-.obj rule for shared engine sources.
# Only the tiny entry object uses its adjacent-object rule, inside this target.
# All shared engine objects remain in build/obj. SDK flags are not force-included.
SRCS := $(CURDIR)/entry.c
LDFLAGS += -stack:1048576 -map:$(CURDIR)/build/nexuiz-xbox.map
include $(NXDK_DIR)/Makefile

GAME_FLAGS := -std=c17 -O1 -g -fno-omit-frame-pointer -Wall -Wextra
GAME_FLAGS += -I$(ROOT_DIR) -I$(IDENTITY_DIR)
GAME_FLAGS += -include $(CURDIR)/profile.h -include $(IDENTITY_DIR)/xbox_build_identity.h
GAME_FLAGS += -DCONFIG_MENU -fno-fast-math

# The SDK entry object is target-local and must also track build identity.
$(CURDIR)/entry.obj: CFLAGS += $(GAME_FLAGS)
$(CURDIR)/entry.obj: $(CURDIR)/profile.h $(IDENTITY_DIR)/xbox_build_identity.h
main.exe: $(GAME_OBJECTS)
$(OBJ_DIR)/%.obj: $(ROOT_DIR)/%.c $(CURDIR)/profile.h $(IDENTITY_DIR)/xbox_build_identity.h
	@mkdir -p "$(@D)"
	$(CC) $(NXDK_CFLAGS) $(GAME_FLAGS) -MMD -MP -MF "$(@:.obj=.d)" -MT "$@" -c "$<" -o "$@"

.PHONY: stage-game-content source-audit clean-game
stage-game-content:
	$(PYTHON) "$(ROOT_DIR)/tools/xbox/stage_game_disc.py" --content "$(CONTENT_DIR)" --disc "$(OUTPUT_DIR)"

# A content-only update must repack the ISO. The phony prerequisite deliberately
# rebuilds it; no timestamp claim is used to skip content verification.
$(GEN_XISO): stage-game-content

source-audit:
	$(PYTHON) "$(ROOT_DIR)/tools/xbox/audit_game_link.py" --root "$(ROOT_DIR)" --manifest "$(CURDIR)/sources.mk" --output "$(CURDIR)/build/source-audit.json"

clean-game:
	rm -rf "$(CURDIR)/build"
	rm -f "$(CURDIR)/main.exe" "$(CURDIR)/main.lib" "$(CURDIR)/entry.obj" "$(CURDIR)/entry.c.d" "$(GEN_XISO)"

# This does not change the diagnostics' own objects, packages or build rules.
-include $(GAME_DEPENDENCIES)
