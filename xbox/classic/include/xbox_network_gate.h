#ifndef XBOX_CLASSIC_NETWORK_GATE_H
#define XBOX_CLASSIC_NETWORK_GATE_H

enum
{
	XBOX_NETWORK_FAILED = -1,
	XBOX_NETWORK_IDLE = 0,
	XBOX_NETWORK_STARTING = 1,
	XBOX_NETWORK_READY = 2
};

typedef struct xbox_network_gate_s
{
	int socket_deferred;
	int retry_consumed;
} xbox_network_gate_t;

void Xbox_NetworkGateInit(xbox_network_gate_t *gate);
int Xbox_NetworkGateCanOpen(xbox_network_gate_t *gate, int network_state);
int Xbox_NetworkGateTakeReadyRetry(xbox_network_gate_t *gate, int network_state);

#endif
