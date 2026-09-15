.DEFAULT_GOAL := all

ROOT_DIR := $(abspath $(CURDIR)/..)
NXDK_DIR ?= $(abspath $(ROOT_DIR)/../nxdk)
NXDK_PIN_FILE := $(CURDIR)/nxdk.version
NXDK_PIN := $(strip $(shell cat "$(NXDK_PIN_FILE)" 2>/dev/null))
ALLOW_UNPINNED_NXDK ?= 0
PYTHON ?= python3

OUTPUT_DIR ?= $(CURDIR)/build
GEN_XISO ?= $(CURDIR)/darkplaces-xbox-foundation.iso
XBE_TITLE = DarkPlaces\ Xbox\ Foundation

ifeq ($(wildcard $(NXDK_PIN_FILE)),)
$(error Missing nxdk pin file: $(NXDK_PIN_FILE))
endif
ifeq ($(NXDK_PIN),)
$(error The nxdk pin file is empty: $(NXDK_PIN_FILE))
endif
ifeq ($(wildcard $(NXDK_DIR)/Makefile),)
$(error NXDK_DIR must point to an nxdk checkout containing Makefile; got $(NXDK_DIR))
endif
ifeq ($(wildcard $(NXDK_DIR)/bin/nxdk-cc),)
$(error NXDK_DIR is missing the nxdk compiler wrapper: $(NXDK_DIR)/bin/nxdk-cc)
endif

# nxdk's Makefile invokes wrapper names such as nxdk-cc and nxdk-link. Export
# both the checkout path and its bin directory so this build entry point works
# without requiring callers to mutate their parent shell first.
export NXDK_DIR
export PATH := $(NXDK_DIR)/bin:$(PATH)

NXDK_ACTUAL := $(strip $(shell git -C "$(NXDK_DIR)" rev-parse HEAD 2>/dev/null))
ifeq ($(NXDK_ACTUAL),)
$(error Unable to read the nxdk Git revision from $(NXDK_DIR))
endif

ifneq ($(NXDK_ACTUAL),$(NXDK_PIN))
ifneq ($(ALLOW_UNPINNED_NXDK),1)
$(error nxdk revision mismatch: expected $(NXDK_PIN), actual $(NXDK_ACTUAL); set ALLOW_UNPINNED_NXDK=1 only for an unscored development build)
else
$(warning Building with unpinned nxdk revision $(NXDK_ACTUAL); expected $(NXDK_PIN))
endif
endif

SOURCE_REVISION := $(strip $(shell git -C "$(ROOT_DIR)" rev-parse HEAD 2>/dev/null || printf unknown))

CFLAGS += -std=c11 -Wall -Wextra -Werror
CFLAGS += -I$(CURDIR)
CFLAGS += -DDP_XBOX_SOURCE_REVISION=\"$(SOURCE_REVISION)\"
CFLAGS += -DDP_XBOX_NXDK_REVISION=\"$(NXDK_ACTUAL)\"

SRCS = \
	$(CURDIR)/smoke/main.c \
	$(CURDIR)/port_contract.c

VERIFY_NXDK_FLAGS =
ifeq ($(ALLOW_UNPINNED_NXDK),1)
VERIFY_NXDK_FLAGS += --allow-mismatch --allow-dirty
endif

.PHONY: verify-nxdk
verify-nxdk:
	@$(PYTHON) $(ROOT_DIR)/tools/xbox/verify_nxdk.py \
		--pin-file $(NXDK_PIN_FILE) \
		--nxdk-dir $(NXDK_DIR) \
		$(VERIFY_NXDK_FLAGS)

include $(NXDK_DIR)/Makefile

$(TARGET): verify-nxdk
