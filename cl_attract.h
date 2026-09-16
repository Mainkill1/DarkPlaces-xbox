/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef CL_ATTRACT_H
#define CL_ATTRACT_H
#include "qtypes.h"
#include "xbox/controller_sdl.h"
struct vid_joystate_s;
void CL_Attract_Init(void);
qbool CL_Attract_Enabled(void);
void CL_Attract_Boot(void);
void CL_Attract_Frame(void);
void CL_Attract_Error(const char *reason);
void CL_Attract_Disconnect(void);
qbool CL_Attract_DemoEnded(void);
qbool CL_Attract_KeyEvent(int key, qbool down);
void CL_Attract_Controller(const dp_pad_sample_t *sample, struct vid_joystate_s *state);
#endif
