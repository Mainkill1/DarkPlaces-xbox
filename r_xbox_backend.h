/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native NV2A device lifecycle and frame-presentation ownership.
 */
#ifndef R_XBOX_BACKEND_H
#define R_XBOX_BACKEND_H

#include "qtypes.h"
#include "r_xbox_internal.h"

struct viddef_mode_s;
typedef struct viddef_mode_s viddef_mode_t;

qbool R_Xbox_Init(const viddef_mode_t *mode);
void R_Xbox_Shutdown(void);
void R_Xbox_BeginFrame(void);
void R_Xbox_EndFrame(qbool wait_for_vblank);
void R_Xbox_InvalidateState(void);
qbool R_Xbox_IsInitialized(void);
qbool R_Xbox_FrameActive(void);
r_xbox_init_stage_t R_Xbox_CompletedStage(void);

#endif
