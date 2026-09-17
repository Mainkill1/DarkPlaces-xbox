# Canonical first end-to-end build entry for the playable Nexuiz Xbox port.
#
# Network access is explicit: `make bootstrap` clones pinned source dependencies
# and downloads the official Nexuiz archive. Every later gate is offline. The
# release wrapper owns XISO creation so changed staged content can never reuse a
# stale image simply because default.xbe did not change.

.DEFAULT_GOAL := help

ROOT_DIR := $(abspath $(CURDIR)/../..)
CLASSIC_DIR := $(ROOT_DIR)/xbox/classic
DEPS_DIR := $(ROOT_DIR)/deps
OUT_DIR := $(CURDIR)/out
LOCK := $(CURDIR)/release-inputs.json
PYTHON ?= python3
CURL ?= curl
GIT ?= git

include $(CLASSIC_DIR)/versions.mk

NXDK_DIR := $(DEPS_DIR)/nxdk
ENGINE_DIR := $(DEPS_DIR)/darkplaces-classic
PBGL_DIR := $(DEPS_DIR)/pbgl
OGG_DIR := $(DEPS_DIR)/ogg
VORBIS_DIR := $(DEPS_DIR)/vorbis
NEXUIZ_ARCHIVE ?= $(DEPS_DIR)/nexuiz-252.zip
DISC_DIR := $(CLASSIC_DIR)/build/disc
XBE := $(DISC_DIR)/default.xbe
XISO := $(CLASSIC_DIR)/nexuiz-xbox.iso
BUILD_IDENTITY := $(DISC_DIR)/BUILD-IDENTITY.txt
CONTENT_IDENTITY := $(DISC_DIR)/CONTENT-IDENTITY.json
EXTRACT_XISO := $(NXDK_DIR)/tools/extract-xiso/build/extract-xiso

COMMON_VARS := \
	NXDK_DIR="$(NXDK_DIR)" \
	ENGINE_DIR="$(ENGINE_DIR)" \
	PBGL_DIR="$(PBGL_DIR)" \
	OGG_DIR="$(OGG_DIR)" \
	VORBIS_DIR="$(VORBIS_DIR)"

.PHONY: help bootstrap deps content preflight stage identity engine xbe verify-tree xiso verify-xiso package all clean clean-output

help:
	@printf '%s\n' \
	  'Nexuiz Xbox release-candidate build' \
	  '' \
	  'Network phases:' \
	  '  make -C xbox/release bootstrap     clone exact source pins + fetch verified Nexuiz 2.5.2' \
	  '  make -C xbox/release deps          clone/checkout exact open-source dependency commits' \
	  '  make -C xbox/release content       download official Nexuiz archive to a temp file and verify it' \
	  '' \
	  'Offline phases:' \
	  '  make -C xbox/release preflight     verify every dependency checkout and archive identity' \
	  '  make -C xbox/release stage         stage complete data tree + Xbox defaults' \
	  '  make -C xbox/release engine        compile/link main.exe only' \
	  '  make -C xbox/release xbe           generate default.xbe from the linked engine' \
	  '  make -C xbox/release verify-tree   reconcile staged data, identities and XBE before packaging' \
	  '  make -C xbox/release xiso          force-create a fresh XDVDFS image from the staged tree' \
	  '  make -C xbox/release verify-xiso   parse/hash the XDVDFS image against the staged tree' \
	  '  make -C xbox/release package       publish XBE/XISO + identities + SHA256SUMS' \
	  '  make -C xbox/release all           complete offline release-candidate pipeline' \
	  '' \
	  'Supply NEXUIZ_ARCHIVE=/path/nexuiz-252.zip to use an existing verified archive.'

bootstrap: deps content preflight

# Clone missing dependency repositories and force only these dedicated checkout
# directories to the exact immutable revisions. They live under ignored /deps.
deps:
	@set -eu; \
	mkdir -p "$(DEPS_DIR)"; \
	clone_pin() { \
		name="$$1"; repo="$$2"; rev="$$3"; recursive="$$4"; dest="$(DEPS_DIR)/$$name"; \
		if [ ! -e "$$dest/.git" ]; then \
			echo "[ CLONE    ] $$repo -> $$dest"; \
			if [ "$$recursive" = yes ]; then \
				$(GIT) clone --filter=blob:none --recurse-submodules "https://github.com/$$repo.git" "$$dest"; \
			else \
				$(GIT) clone --filter=blob:none "https://github.com/$$repo.git" "$$dest"; \
			fi; \
		fi; \
		test -d "$$dest/.git" || { echo "Not a Git checkout: $$dest" >&2; exit 2; }; \
		if [ -n "$$($(GIT) -C "$$dest" status --porcelain --untracked-files=no)" ]; then \
			echo "Tracked dependency files are modified; refusing to overwrite $$dest" >&2; exit 2; \
		fi; \
		$(GIT) -C "$$dest" fetch --depth=1 origin "$$rev"; \
		$(GIT) -C "$$dest" checkout --detach --force "$$rev"; \
		if [ "$$recursive" = yes ]; then \
			$(GIT) -C "$$dest" submodule update --init --recursive; \
		fi; \
	}; \
	clone_pin nxdk XboxDev/nxdk "$(shell cat $(ROOT_DIR)/xbox/nxdk.version)" yes; \
	clone_pin darkplaces-classic DarkPlacesEngine/DarkPlaces "$(DP_CLASSIC_REV)" no; \
	clone_pin pbgl fgsfdsfgs/pbgl "$(PBGL_REV)" no; \
	clone_pin ogg xiph/ogg "$(OGG_REV)" no; \
	clone_pin vorbis xiph/vorbis "$(VORBIS_REV)" no

# Never trust a partially downloaded or changed archive. Existing archives are
# verified first; a new download is written to a temporary path, verified, then
# atomically renamed into place.
content:
	@set -eu; \
	mkdir -p "$(dir $(NEXUIZ_ARCHIVE))"; \
	if [ -f "$(NEXUIZ_ARCHIVE)" ]; then \
		if $(PYTHON) "$(ROOT_DIR)/tools/xbox/release_inputs.py" --lock "$(LOCK)" verify-archive "$(NEXUIZ_ARCHIVE)"; then \
			echo "[ CONTENT  ] existing Nexuiz archive verified"; \
			exit 0; \
		fi; \
		echo "Existing archive failed verification; refusing to overwrite it: $(NEXUIZ_ARCHIVE)" >&2; \
		exit 2; \
	fi; \
	tmp="$(NEXUIZ_ARCHIVE).download.$$PPID"; \
	trap 'rm -f "'"'"$$tmp"'"'"' EXIT INT TERM; \
	echo "[ DOWNLOAD ] $(NEXUIZ_252_URL)"; \
	$(CURL) --fail --location --retry 5 --retry-delay 2 --output "$$tmp" "$(NEXUIZ_252_URL)"; \
	$(PYTHON) "$(ROOT_DIR)/tools/xbox/release_inputs.py" --lock "$(LOCK)" verify-archive "$$tmp"; \
	mv "$$tmp" "$(NEXUIZ_ARCHIVE)"; \
	trap - EXIT INT TERM; \
	echo "[ CONTENT  ] $(NEXUIZ_ARCHIVE)"

preflight:
	@$(PYTHON) "$(ROOT_DIR)/tools/xbox/release_inputs.py" --lock "$(LOCK)" verify-lock
	@$(PYTHON) "$(ROOT_DIR)/tools/xbox/release_inputs.py" --lock "$(LOCK)" verify-checkouts "$(ROOT_DIR)"
	@$(PYTHON) "$(ROOT_DIR)/tools/xbox/release_inputs.py" --lock "$(LOCK)" verify-archive "$(NEXUIZ_ARCHIVE)"

stage: preflight
	@echo "[ STAGE    ] complete Nexuiz 2.5.2 data tree"
	@$(PYTHON) "$(ROOT_DIR)/tools/xbox/stage_classic_release.py" \
		--lock "$(LOCK)" --archive "$(NEXUIZ_ARCHIVE)" --disc "$(DISC_DIR)"

identity: stage
	@echo "[ IDENTITY ] $(BUILD_IDENTITY)"
	@{ \
		echo "release=nexuiz-xbox-2.5.2"; \
		echo "port_commit=$$($(GIT) -C "$(ROOT_DIR)" rev-parse HEAD)"; \
		echo "nxdk=$(shell cat $(ROOT_DIR)/xbox/nxdk.version)"; \
		echo "darkplaces=$(DP_CLASSIC_REV)"; \
		echo "pbgl=$(PBGL_REV)"; \
		echo "ogg=$(OGG_REV)"; \
		echo "vorbis=$(VORBIS_REV)"; \
		echo "nexuiz_sha256=$(NEXUIZ_252_SHA256)"; \
		echo "nexuiz_md5=$(NEXUIZ_252_MD5)"; \
		echo "content_identity_sha256=$$(sha256sum "$(CONTENT_IDENTITY)" | awk '{print $$1}')"; \
	} > "$(BUILD_IDENTITY)"

engine: preflight
	@echo "[ ENGINE   ] Nexuiz-era DarkPlaces + Xbox platform backend"
	@$(MAKE) -C "$(CLASSIC_DIR)" V=1 main.exe $(COMMON_VARS)

# Build only the executable container here. The generic nxdk `all` target also
# owns GEN_XISO and only tracks default.xbe as an XISO prerequisite, which is not
# sufficient for a staged game-data tree that may change independently.
xbe: stage identity engine
	@echo "[ XBE      ] $(XBE)"
	@$(MAKE) -C "$(CLASSIC_DIR)" V=1 "$(XBE)" $(COMMON_VARS)
	@test -s "$(XBE)" || { echo "Missing/empty XBE: $(XBE)" >&2; exit 2; }

verify-tree: xbe identity
	@echo "[ VERIFY   ] staged release tree"
	@$(PYTHON) "$(ROOT_DIR)/tools/xbox/verify_release_tree.py" "$(DISC_DIR)"

# Always remove and recreate the XISO after staging. This intentionally avoids
# timestamp-only dependency inference for the hundreds of staged game files.
xiso: verify-tree
	@echo "[ XISO     ] fresh XDVDFS image"
	@$(MAKE) -C "$(CLASSIC_DIR)" V=1 extract-xiso $(COMMON_VARS)
	@rm -f "$(XISO)"
	@$(EXTRACT_XISO) -c "$(DISC_DIR)" "$(XISO)"
	@test -s "$(XISO)" || { echo "Missing/empty XISO: $(XISO)" >&2; exit 2; }

verify-xiso: xiso
	@echo "[ VERIFY   ] packaged XDVDFS image"
	@$(PYTHON) "$(ROOT_DIR)/tools/xbox/verify_xiso.py" "$(XISO)" "$(DISC_DIR)"

package: verify-xiso
	@echo "[ PACKAGE  ] publish verified XBE/XISO"
	@rm -rf "$(OUT_DIR)"
	@mkdir -p "$(OUT_DIR)"
	@cp "$(XBE)" "$(OUT_DIR)/nexuiz-xbox.xbe"
	@cp "$(XISO)" "$(OUT_DIR)/nexuiz-xbox.iso"
	@cp "$(BUILD_IDENTITY)" "$(OUT_DIR)/BUILD-IDENTITY.txt"
	@cp "$(CONTENT_IDENTITY)" "$(OUT_DIR)/CONTENT-IDENTITY.json"
	@cd "$(OUT_DIR)" && sha256sum nexuiz-xbox.xbe nexuiz-xbox.iso BUILD-IDENTITY.txt CONTENT-IDENTITY.json > SHA256SUMS
	@echo "[ READY    ] $(OUT_DIR)"

all: package

clean-output:
	@rm -rf "$(OUT_DIR)"

clean: clean-output
	@$(MAKE) -C "$(CLASSIC_DIR)" clean $(COMMON_VARS) || true
	@rm -rf "$(CLASSIC_DIR)/build"
	@rm -f "$(XISO)"
