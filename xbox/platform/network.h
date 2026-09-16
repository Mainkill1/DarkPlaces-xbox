/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef DP_XBOX_NETWORK_H
#define DP_XBOX_NETWORK_H
void DP_XboxNetworkStart(void);
void DP_XboxNetworkPoll(void);
int DP_XboxNetworkReady(void);
int DP_XboxNetworkResult(void);
void DP_XboxNetworkStop(void);
#endif
