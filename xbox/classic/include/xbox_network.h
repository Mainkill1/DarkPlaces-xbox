#ifndef XBOX_CLASSIC_NETWORK_H
#define XBOX_CLASSIC_NETWORK_H

void Xbox_StartNetworkAsync(void);
void Xbox_ShutdownNetwork(void);
int Xbox_NetworkSocket(int domain, int type, int protocol);
int Xbox_NetworkTakeReadyRetry(void);

#endif
