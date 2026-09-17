# Explicit native engine ownership. Paths are repository-relative, never globbed.
# Keep this manifest auditable: SDK sources are compiled by nxdk, separately.

DP_XBOX_PLATFORM_COMMON_SRCS := \
    xbox/game/entry.c sys_xbox.c thread_null.c snd_null.c \
    xbox/controller_sdl.c xbox/attract_policy.c \
    xbox/platform/platform.c xbox/platform/network.c \
    xbox/platform/no_downloads.c xbox/platform/no_video_decode.c

# The bootstrap backend remains an explicit diagnostic mode until the native
# renderer is complete. It must never be linked beside the production backend.
DP_XBOX_BOOTSTRAP_VIDEO_SRCS := vid_xbox_bootstrap.c

# These files are the complete direct NV2A ownership boundary. Some are added
# by later renderer tasks; naming them here makes the final link set explicit.
DP_XBOX_NATIVE_RENDER_SRCS := \
    vid_xbox.c r_xbox_stats.c r_xbox_backend.c r_xbox_texture.c \
    r_xbox_program.c r_xbox_material.c r_xbox_draw2d.c \
    r_xbox_world.c r_xbox_models.c

DP_XBOX_CORE_SRCS := \
    builddate.c cmd.c cvar.c common.c console.c host.c zone.c \
    fs.c filematch.c com_game.c com_infostring.c com_msg.c com_crc16.c \
    com_ents.c com_ents4.c com_ents5.c crypto.c hmac.c mdfour.c \
    mathlib.c matrixlib.c utf8lib.c taskqueue.c lhnet.c netconn.c \
    protocol.c prvm_cmds.c prvm_edict.c prvm_exec.c \
    collision.c world.c phys.c bih.c svbsp.c polygon.c portals.c curves.c

DP_XBOX_CLIENT_SRCS := \
    cl_cmd.c cl_collision.c cl_demo.c cl_attract.c cl_graphics_menu.c \
    cl_ents.c cl_ents4.c cl_ents5.c cl_ents_nq.c cl_ents_qw.c \
    cl_input.c cl_main.c cl_parse.c cl_particles.c cl_screen.c \
    cl_video.c clvm_cmds.c csprogs.c keys.c view.c sbar.c \
    menu.c mvm_cmds.c vid_shared.c cd_shared.c dpvsimpledecode.c

DP_XBOX_SERVER_SRCS := \
    sv_ccmds.c sv_demo.c sv_ents.c sv_ents4.c sv_ents5.c sv_ents_csqc.c \
    sv_ents_nq.c sv_main.c sv_move.c sv_phys.c sv_save.c sv_send.c \
    sv_user.c svvm_cmds.c

DP_XBOX_RESOURCE_SRCS := \
    model_alias.c model_brush.c model_shared.c model_sprite.c \
    mod_skeletal_animatevertices_generic.c mod_skeletal_animatevertices_sse.c \
    image.c image_png.c jpeg.c palette.c wad.c fractalnoise.c ft2.c \
    meshqueue.c r_modules.c r_explosion.c r_lightning.c r_shadow.c \
    r_sky.c r_sprites.c r_stats.c

# High-level traversal remains shared. Native mode replaces only device/state,
# texture ownership and shader/material selection.
DP_XBOX_HIGHLEVEL_RENDER_SRCS := \
    gl_draw.c gl_rmain.c gl_rsurf.c

# Bootstrap mode retains upstream symbol owners but does not initialize a GL
# render path. This group is prohibited from native mode.
DP_XBOX_DORMANT_RENDER_SRCS := \
    gl_backend.c gl_draw.c gl_rmain.c gl_rsurf.c gl_textures.c

DP_XBOX_BASE_SRCS := \
    $(DP_XBOX_PLATFORM_COMMON_SRCS) $(DP_XBOX_CORE_SRCS) \
    $(DP_XBOX_CLIENT_SRCS) $(DP_XBOX_SERVER_SRCS) \
    $(DP_XBOX_RESOURCE_SRCS)

DP_XBOX_BOOTSTRAP_SOURCES := \
    $(DP_XBOX_BASE_SRCS) $(DP_XBOX_BOOTSTRAP_VIDEO_SRCS) \
    $(DP_XBOX_DORMANT_RENDER_SRCS)

DP_XBOX_NATIVE_SOURCES := \
    $(DP_XBOX_BASE_SRCS) $(DP_XBOX_NATIVE_RENDER_SRCS) \
    $(DP_XBOX_HIGHLEVEL_RENDER_SRCS)
