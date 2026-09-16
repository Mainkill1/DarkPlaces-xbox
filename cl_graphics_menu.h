/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef CL_GRAPHICS_MENU_H
#define CL_GRAPHICS_MENU_H
#include "qtypes.h"
void CL_GraphicsMenu_Init(void);
void CL_GraphicsMenu_BootConfig(void);
void CL_GraphicsMenu_Open(void);
void CL_GraphicsMenu_Close(void);
qbool CL_GraphicsMenu_Editing(void);
unsigned CL_GraphicsMenu_Context(void);
qbool CL_GraphicsMenu_KeyEvent(int key, qbool down);
qbool CL_GraphicsMenu_Draw(void);
void CL_GraphicsMenu_LogSettings(void);
#endif
