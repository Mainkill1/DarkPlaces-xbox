/* Main-thread policy for bringing up Internet sockets after asynchronous nxdk
 * network initialization.  Loopback sockets remain owned by DarkPlaces. */

#include "include/xbox_network_gate.h"

void Xbox_NetworkGateInit(xbox_network_gate_t *gate)
{
	gate->socket_deferred = 0;
	gate->retry_consumed = 0;
}

int Xbox_NetworkGateCanOpen(xbox_network_gate_t *gate, int network_state)
{
	if (network_state == XBOX_NETWORK_READY)
		return 1;
	gate->socket_deferred = 1;
	return 0;
}

int Xbox_NetworkGateTakeReadyRetry(xbox_network_gate_t *gate, int network_state)
{
	if (network_state != XBOX_NETWORK_READY || !gate->socket_deferred || gate->retry_consumed)
		return 0;
	gate->retry_consumed = 1;
	return 1;
}
