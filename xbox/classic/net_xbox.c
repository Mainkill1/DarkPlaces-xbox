#include <errno.h>
#include <windows.h>
#include <hal/debug.h>
#include <lwip/sockets.h>
#include <lwip/inet.h>
#include <nxdk/net.h>

#include "quakedef.h"
#include "include/xbox_network.h"
#include "include/xbox_network_gate.h"

static volatile LONG xbox_net_state;
static HANDLE xbox_net_thread;
static xbox_network_gate_t xbox_net_gate;
static int xbox_net_defer_reported;

static DWORD WINAPI Xbox_NetThread(void *unused)
{
	int result;

	(void)unused;
	InterlockedExchange(&xbox_net_state, XBOX_NETWORK_STARTING);
	result = nxNetInit(NULL);
	InterlockedExchange(&xbox_net_state,
		result == 0 ? XBOX_NETWORK_READY : XBOX_NETWORK_FAILED);
	debugPrint(result == 0 ? "Xbox network: ready\n" : "Xbox network: unavailable; offline mode remains active\n");
	return 0;
}

void Xbox_StartNetworkAsync(void)
{
	if (InterlockedCompareExchange(&xbox_net_state, XBOX_NETWORK_IDLE, XBOX_NETWORK_IDLE) != XBOX_NETWORK_IDLE)
		return;
	Xbox_NetworkGateInit(&xbox_net_gate);
	xbox_net_thread = CreateThread(NULL, 64 * 1024, Xbox_NetThread, NULL, 0, NULL);
	if (!xbox_net_thread)
		InterlockedExchange(&xbox_net_state, XBOX_NETWORK_FAILED);
}

void Xbox_ShutdownNetwork(void)
{
	if (xbox_net_thread)
	{
		CloseHandle(xbox_net_thread);
		xbox_net_thread = NULL;
	}
}

int Xbox_NetworkSocket(int domain, int type, int protocol)
{
	int state = (int)InterlockedCompareExchange(&xbox_net_state, 0, 0);

	if (!Xbox_NetworkGateCanOpen(&xbox_net_gate, state))
	{
		if (!xbox_net_defer_reported)
		{
			xbox_net_defer_reported = 1;
			Con_Print("Xbox network initialization pending; deferring Internet sockets\n");
		}
		errno = ENETDOWN;
		return -1;
	}
	return lwip_socket(domain, type, protocol);
}

int Xbox_NetworkTakeReadyRetry(void)
{
	int state = (int)InterlockedCompareExchange(&xbox_net_state, 0, 0);
	return Xbox_NetworkGateTakeReadyRetry(&xbox_net_gate, state);
}

/*
 * Socket ownership lives in the historical DarkPlaces lhnet.c and maps to
 * lwIP through the compatibility headers under xbox/classic/include.
 * nxNetInit is intentionally started asynchronously by sys_xbox.c so a
 * missing DHCP lease never blocks offline play or zero-action demo startup.
 */
int DP_XboxClassicNetworkBackend(void)
{
	return 1;
}
