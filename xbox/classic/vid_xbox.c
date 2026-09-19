#define GL_GLEXT_PROTOTYPES
#include <pbgl.h>
#include <GL/gl.h>
#include <GL/glext.h>
#include <hal/video.h>
#include <SDL.h>
#include <math.h>
#include <string.h>

#include "quakedef.h"
#include "../attract_policy.h"
#include "include/xbox_boot_trace.h"
#include "include/xbox_gl_bootstrap.h"
#include "include/xbox_gl_state.h"
#include "include/xbox_network.h"

int cl_available = true;
qboolean vid_supportrefreshrate = false;

cvar_t joy_detected = {CVAR_READONLY, "joy_detected", "0", "number of controllers detected"};
cvar_t joy_enable = {CVAR_SAVE, "joy_enable", "1", "enables controller support"};
cvar_t joy_index = {0, "joy_index", "0", "controller index"};
cvar_t joy_axisforward = {0, "joy_axisforward", "1", "left stick vertical"};
cvar_t joy_axisside = {0, "joy_axisside", "0", "left stick horizontal"};
cvar_t joy_axisup = {0, "joy_axisup", "-1", "unused"};
cvar_t joy_axispitch = {0, "joy_axispitch", "3", "right stick vertical"};
cvar_t joy_axisyaw = {0, "joy_axisyaw", "2", "right stick horizontal"};
cvar_t joy_axisroll = {0, "joy_axisroll", "-1", "unused"};
cvar_t joy_deadzoneforward = {0, "joy_deadzoneforward", "0.20", "left stick deadzone"};
cvar_t joy_deadzoneside = {0, "joy_deadzoneside", "0.20", "left stick deadzone"};
cvar_t joy_deadzoneup = {0, "joy_deadzoneup", "0.20", "unused"};
cvar_t joy_deadzonepitch = {0, "joy_deadzonepitch", "0.20", "right stick deadzone"};
cvar_t joy_deadzoneyaw = {0, "joy_deadzoneyaw", "0.20", "right stick deadzone"};
cvar_t joy_deadzoneroll = {0, "joy_deadzoneroll", "0.20", "unused"};
cvar_t joy_sensitivityforward = {0, "joy_sensitivityforward", "-1", "movement multiplier"};
cvar_t joy_sensitivityside = {0, "joy_sensitivityside", "1", "movement multiplier"};
cvar_t joy_sensitivityup = {0, "joy_sensitivityup", "1", "unused"};
cvar_t joy_sensitivitypitch = {0, "joy_sensitivitypitch", "1.4", "look multiplier"};
cvar_t joy_sensitivityyaw = {0, "joy_sensitivityyaw", "-1.4", "look multiplier"};
cvar_t joy_sensitivityroll = {0, "joy_sensitivityroll", "1", "unused"};

static SDL_GameController *controller;
static unsigned char oldbuttons[16];
static qboolean pbgl_started;
static qboolean first_swap_traced;
static dp_button_gate_t attract_button_gate;
static qboolean attract_consume_until_release;
static qboolean attract_manual_stop;

static double Xbox_Axis(SDL_GameControllerAxis axis, double sensitivity, double deadzone)
{
	double value;
	if (!controller)
		return 0;
	value = SDL_GameControllerGetAxis(controller, axis) / 32767.0;
	value = bound(-1, value, 1);
	if (fabs(value) < deadzone)
		return 0;
	value = (fabs(value) - deadzone) / (1.0 - deadzone) * (value < 0 ? -1 : 1);
	return value * sensitivity;
}

static uint32_t Xbox_ButtonMask(qboolean *lt, qboolean *rt)
{
	uint32_t mask = 0;
#define XBOX_BUTTON_BIT(slot, button) \
	do { if (SDL_GameControllerGetButton(controller, (button))) mask |= (1u << (slot)); } while (0)
	XBOX_BUTTON_BIT(0, SDL_CONTROLLER_BUTTON_A);
	XBOX_BUTTON_BIT(1, SDL_CONTROLLER_BUTTON_B);
	XBOX_BUTTON_BIT(2, SDL_CONTROLLER_BUTTON_X);
	XBOX_BUTTON_BIT(3, SDL_CONTROLLER_BUTTON_Y);
	/* nxdk maps Original Xbox White/Black onto the SDL shoulder slots. */
	XBOX_BUTTON_BIT(4, SDL_CONTROLLER_BUTTON_LEFTSHOULDER);
	XBOX_BUTTON_BIT(5, SDL_CONTROLLER_BUTTON_RIGHTSHOULDER);
	XBOX_BUTTON_BIT(6, SDL_CONTROLLER_BUTTON_LEFTSTICK);
	XBOX_BUTTON_BIT(7, SDL_CONTROLLER_BUTTON_RIGHTSTICK);
	XBOX_BUTTON_BIT(8, SDL_CONTROLLER_BUTTON_DPAD_UP);
	XBOX_BUTTON_BIT(9, SDL_CONTROLLER_BUTTON_DPAD_DOWN);
	XBOX_BUTTON_BIT(10, SDL_CONTROLLER_BUTTON_DPAD_LEFT);
	XBOX_BUTTON_BIT(11, SDL_CONTROLLER_BUTTON_DPAD_RIGHT);
	XBOX_BUTTON_BIT(12, SDL_CONTROLLER_BUTTON_START);
	XBOX_BUTTON_BIT(13, SDL_CONTROLLER_BUTTON_BACK);
#undef XBOX_BUTTON_BIT
	*lt = SDL_GameControllerGetAxis(controller, SDL_CONTROLLER_AXIS_TRIGGERLEFT) > 8192;
	*rt = SDL_GameControllerGetAxis(controller, SDL_CONTROLLER_AXIS_TRIGGERRIGHT) > 8192;
	if (*lt)
		mask |= 1u << 14;
	if (*rt)
		mask |= 1u << 15;
	return mask;
}

static void Xbox_OpenController(void)
{
	int i;
	if (controller && SDL_GameControllerGetAttached(controller))
		return;
	if (controller)
	{
		SDL_GameControllerClose(controller);
		controller = NULL;
	}
	DP_ButtonGate_Reset(&attract_button_gate);
	attract_consume_until_release = false;
	memset(oldbuttons, 0, sizeof(oldbuttons));
	for (i = 0; i < SDL_NumJoysticks(); ++i)
	{
		if (SDL_IsGameController(i))
		{
			controller = SDL_GameControllerOpen(i);
			if (controller)
				break;
		}
	}
	Cvar_SetValueQuick(&joy_detected, controller ? 1 : 0);
}

static qboolean Xbox_AttractActive(void)
{
	return cls.demoplayback || cls.demonum >= 0;
}

static void Xbox_AttractTakeover(void)
{
	/* Stop both the current playback and the automatic CL_NextDemo loop. */
	cls.demonum = -1;
	if (cls.demoplayback)
		CL_Disconnect();
	if (key_dest != key_menu && key_dest != key_menu_grabbed)
		MR_ToggleMenu_f();
	attract_manual_stop = true;
	Con_Print("XBOX_ATTRACT_TAKEOVER\n");
}

static qboolean Xbox_AttractRestartRequested(uint32_t pressed)
{
	return attract_manual_stop
		&& (pressed & (1u << 12))
		&& key_dest == key_menu
		&& cls.state == ca_disconnected
		&& !sv.active;
}

static void Xbox_AttractRestart(void)
{
	/* xbox_demo_start is generated into xbox-defaults.cfg and is the same
	 * playlist command used for the initial zero-input startup. */
	attract_manual_stop = false;
	Cbuf_AddText("xbox_demo_start\n");
	MR_ToggleMenu_f();
	attract_consume_until_release = true;
	memset(oldbuttons, 0, sizeof(oldbuttons));
	Con_Print("XBOX_ATTRACT_RESTART\n");
}

static void Xbox_KeyEdge(int slot, qboolean down, int gamekey, int menukey)
{
	int key = key_dest == key_menu ? menukey : gamekey;
	if (slot < 0 || slot >= (int)sizeof(oldbuttons) || key <= 0)
		return;
	if (!!oldbuttons[slot] != !!down)
	{
		oldbuttons[slot] = down != 0;
		Key_Event(key, 0, down);
	}
}

void Sys_SendKeyEvents(void)
{
	SDL_Event event;
	SDL_Joystick *joystick;
	int32_t instance;
	uint32_t buttonmask, pressed;
	qboolean lt, rt;
	if (Xbox_NetworkTakeReadyRetry())
	{
		Con_Print("Xbox network ready; reopening client sockets\n");
		NetConn_CloseClientPorts();
		NetConn_OpenClientPorts();
	}
	while (SDL_PollEvent(&event))
	{
		if (event.type == SDL_CONTROLLERDEVICEADDED || event.type == SDL_CONTROLLERDEVICEREMOVED)
			Xbox_OpenController();
		else if (event.type == SDL_QUIT)
			Sys_Quit(0);
	}
	Xbox_OpenController();
	if (!controller || !joy_enable.integer)
	{
		DP_ButtonGate_Update(&attract_button_gate, false, -1, 0);
		attract_consume_until_release = false;
		return;
	}
	SDL_GameControllerUpdate();
	buttonmask = Xbox_ButtonMask(&lt, &rt);
	joystick = SDL_GameControllerGetJoystick(controller);
	instance = joystick ? (int32_t)SDL_JoystickInstanceID(joystick) : -1;
	pressed = DP_ButtonGate_Update(&attract_button_gate, true, instance, buttonmask);

	/* Once the user actually enters a local or remote game, Start must return
	 * to normal game/menu semantics rather than retaining an old attract stop. */
	if (attract_manual_stop && (cls.state != ca_disconnected || sv.active))
		attract_manual_stop = false;

	/* A takeover press is consumed completely. Releases cannot leak into the
	 * menu, and a button already held at startup/reconnect never counts as a
	 * fresh takeover action. Analog stick drift is not part of buttonmask. */
	if (attract_consume_until_release)
	{
		if (!buttonmask)
		{
			attract_consume_until_release = false;
			memset(oldbuttons, 0, sizeof(oldbuttons));
		}
		return;
	}
	if (Xbox_AttractActive() && pressed)
	{
		Xbox_AttractTakeover();
		attract_consume_until_release = true;
		memset(oldbuttons, 0, sizeof(oldbuttons));
		return;
	}
	if (Xbox_AttractRestartRequested(pressed))
	{
		Xbox_AttractRestart();
		return;
	}

	Xbox_KeyEdge(0, (buttonmask & (1u << 0)) != 0, K_JOY1, K_ENTER);
	Xbox_KeyEdge(1, (buttonmask & (1u << 1)) != 0, K_JOY2, K_ESCAPE);
	Xbox_KeyEdge(2, (buttonmask & (1u << 2)) != 0, K_JOY3, K_ENTER);
	Xbox_KeyEdge(3, (buttonmask & (1u << 3)) != 0, K_JOY4, K_ESCAPE);
	Xbox_KeyEdge(4, (buttonmask & (1u << 4)) != 0, K_JOY5, K_LEFTARROW);
	Xbox_KeyEdge(5, (buttonmask & (1u << 5)) != 0, K_JOY6, K_RIGHTARROW);
	Xbox_KeyEdge(6, (buttonmask & (1u << 6)) != 0, K_JOY7, 0);
	Xbox_KeyEdge(7, (buttonmask & (1u << 7)) != 0, K_JOY8, 0);
	Xbox_KeyEdge(8, (buttonmask & (1u << 8)) != 0, K_AUX3, K_UPARROW);
	Xbox_KeyEdge(9, (buttonmask & (1u << 9)) != 0, K_AUX4, K_DOWNARROW);
	Xbox_KeyEdge(10, (buttonmask & (1u << 10)) != 0, K_AUX5, K_LEFTARROW);
	Xbox_KeyEdge(11, (buttonmask & (1u << 11)) != 0, K_AUX6, K_RIGHTARROW);
	Xbox_KeyEdge(12, (buttonmask & (1u << 12)) != 0, K_ESCAPE, K_ESCAPE);
	Xbox_KeyEdge(13, (buttonmask & (1u << 13)) != 0, K_ESCAPE, K_ESCAPE);
	Xbox_KeyEdge(14, lt, K_AUX1, 0);
	Xbox_KeyEdge(15, rt, K_AUX2, 0);
}

void IN_Move(void)
{
	if (!controller || !joy_enable.integer)
		return;
	cl.cmd.forwardmove += Xbox_Axis(SDL_CONTROLLER_AXIS_LEFTY, joy_sensitivityforward.value, joy_deadzoneforward.value) * cl_forwardspeed.value;
	cl.cmd.sidemove += Xbox_Axis(SDL_CONTROLLER_AXIS_LEFTX, joy_sensitivityside.value, joy_deadzoneside.value) * cl_sidespeed.value;
	cl.viewangles[0] += Xbox_Axis(SDL_CONTROLLER_AXIS_RIGHTY, joy_sensitivitypitch.value, joy_deadzonepitch.value) * cl.realframetime * cl_pitchspeed.value;
	cl.viewangles[1] += Xbox_Axis(SDL_CONTROLLER_AXIS_RIGHTX, joy_sensitivityyaw.value, joy_deadzoneyaw.value) * cl.realframetime * cl_yawspeed.value;
	in_mouse_x = in_mouse_y = 0;
	in_windowmouse_x = vid.width / 2;
	in_windowmouse_y = vid.height / 2;
}

void VID_SetMouse(qboolean fullscreengrab, qboolean relative, qboolean hidecursor)
{
	(void)fullscreengrab; (void)relative; (void)hidecursor;
}

void VID_Init(void)
{
	Xbox_BootTraceMark("VID_Init enter");
	Cvar_RegisterVariable(&joy_detected);
	Cvar_RegisterVariable(&joy_enable);
	Cvar_RegisterVariable(&joy_index);
	Cvar_RegisterVariable(&joy_axisforward);
	Cvar_RegisterVariable(&joy_axisside);
	Cvar_RegisterVariable(&joy_axisup);
	Cvar_RegisterVariable(&joy_axispitch);
	Cvar_RegisterVariable(&joy_axisyaw);
	Cvar_RegisterVariable(&joy_deadzoneforward);
	Cvar_RegisterVariable(&joy_deadzoneside);
	Cvar_RegisterVariable(&joy_deadzoneup);
	Cvar_RegisterVariable(&joy_deadzonepitch);
	Cvar_RegisterVariable(&joy_deadzoneyaw);
	Cvar_RegisterVariable(&joy_sensitivityforward);
	Cvar_RegisterVariable(&joy_sensitivityside);
	Cvar_RegisterVariable(&joy_sensitivityup);
	Cvar_RegisterVariable(&joy_sensitivitypitch);
	Cvar_RegisterVariable(&joy_sensitivityyaw);
	DP_ButtonGate_Reset(&attract_button_gate);
	attract_consume_until_release = false;
	attract_manual_stop = false;
	if (SDL_InitSubSystem(SDL_INIT_EVENTS | SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER) < 0)
		Con_Printf("SDL controller init failed: %s\n", SDL_GetError());
	Xbox_OpenController();
	Xbox_BootTraceMark("VID_Init complete");
}

int VID_InitMode(int fullscreen, int *width, int *height, int bpp, int refreshrate, int stereobuffer, int samples)
{
	int pbgl_result = 0;
	int bootstrap_result;

	(void)fullscreen; (void)bpp; (void)refreshrate; (void)stereobuffer; (void)samples;
	Xbox_BootTraceMark("VID_InitMode enter");
	*width = 640;
	*height = 480;
	Xbox_BootTraceMark("XVideoSetMode begin");
	if (!XVideoSetMode(640, 480, 32, REFRESH_DEFAULT))
	{
		Xbox_BootTraceMark("XVideoSetMode failed");
		Con_Print("XVideoSetMode failed\n");
		return false;
	}
	Xbox_BootTraceMark("XVideoSetMode complete");
	if (!pbgl_started)
	{
		Xbox_BootTraceMark("pbgl_init begin");
		pbgl_result = pbgl_init(GL_TRUE);
		Xbox_BootTraceMark("pbgl_init returned %d", pbgl_result);
	}
	bootstrap_result = Xbox_GLBootstrap(pbgl_result);
	if (bootstrap_result != XBOX_GL_BOOTSTRAP_OK)
	{
		Con_Printf("Xbox GL bootstrap failed: %d\n", bootstrap_result);
		if (!pbgl_started && pbgl_result == 0)
			pbgl_shutdown();
		return false;
	}
	if (!pbgl_started)
		Xbox_GLStateReset();
	pbgl_started = true;
	gl_platform = "pbGL/NV2A";
	gl_platformextensions = "";
	gl_videosyncavailable = false;
	Xbox_BootTraceMark("GL_Init begin");
	GL_Init();
	Xbox_BootTraceMark("GL_Init complete");
	vid_hidden = false;
	vid_activewindow = true;
	Xbox_BootTraceMark("VID_InitMode complete");
	return true;
}

void VID_Shutdown(void)
{
	if (controller)
	{
		SDL_GameControllerClose(controller);
		controller = NULL;
	}
	DP_ButtonGate_Reset(&attract_button_gate);
	attract_consume_until_release = false;
	attract_manual_stop = false;
	if (pbgl_started)
	{
		pbgl_shutdown();
		pbgl_started = false;
	}
	gl_extensions = "";
	gl_platform = "";
	gl_platformextensions = "";
}

int VID_SetGamma(unsigned short *ramps, int rampsize)
{
	(void)ramps; (void)rampsize;
	return false;
}

int VID_GetGamma(unsigned short *ramps, int rampsize)
{
	(void)ramps; (void)rampsize;
	return false;
}

void VID_Finish(void)
{
	vid_hidden = false;
	vid_activewindow = true;
	if (r_render.integer)
	{
		if (!first_swap_traced)
			Xbox_BootTraceMark("first pbgl_swap_buffers begin");
		if (r_speeds.integer == 2 || gl_finish.integer)
			qglFinish();
		pbgl_swap_buffers();
		if (!first_swap_traced)
		{
			first_swap_traced = true;
			Xbox_BootTraceMark("first pbgl_swap_buffers complete");
		}
	}
}

size_t VID_ListModes(vid_mode_t *modes, size_t maxcount)
{
	if (!modes || maxcount == 0)
		return 0;
	modes[0].width = 640;
	modes[0].height = 480;
	modes[0].bpp = 32;
	modes[0].refreshrate = 60;
	modes[0].pixelheight_num = 1;
	modes[0].pixelheight_denom = 1;
	return 1;
}
