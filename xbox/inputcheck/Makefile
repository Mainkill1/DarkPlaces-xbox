# Standalone hardware input diagnostic; deliberately separate from the smoke XBE.
.DEFAULT_GOAL := all
ROOT_DIR := $(abspath $(CURDIR)/../..)
NXDK_DIR ?= $(abspath $(ROOT_DIR)/../nxdk)
export NXDK_DIR
export PATH := $(NXDK_DIR)/bin:$(PATH)
PYTHON ?= python3
NXDK_SDL := y
XBE_TITLE := DarkPlaces\ Controller\ Check
OUTPUT_DIR := $(CURDIR)/disc
GEN_XISO := $(CURDIR)/controller-check.iso
SRCS := $(CURDIR)/main.c $(ROOT_DIR)/xbox/controller_sdl.c $(ROOT_DIR)/xbox/attract_policy.c
APP_OBJS := $(SRCS:.c=.obj)
$(APP_OBJS): CFLAGS += -std=c11 -Wall -Wextra -Werror -I$(ROOT_DIR)

# Verify BEFORE any make rules compile SDK or app code. There is no override in
# this diagnostic: it is evidence for the same pinned SDL/nxdk used by the port.
SDK_VERIFIED := $(shell $(PYTHON) "$(ROOT_DIR)/tools/xbox/verify_nxdk.py" \
    --pin-file "$(ROOT_DIR)/xbox/nxdk.version" --nxdk-dir "$(NXDK_DIR)" >&2 && printf yes)
ifneq ($(SDK_VERIFIED),yes)
$(error nxdk preflight failed)
endif
include $(NXDK_DIR)/Makefile
