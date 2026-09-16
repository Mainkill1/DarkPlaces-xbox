/* SPDX-License-Identifier: GPL-2.0-or-later
 * Initialize the native stack on its own OS worker, never on a render frame.
 * nxNetShutdown in the pinned SDK does not destroy its service threads, so this
 * owner initializes once per process and never retries by creating more stacks.
 */
#include <windows.h>
#include <nxdk/net.h>
#include <lwip/netif.h>
#include <lwip/tcpip.h>
#include "network.h"

extern struct netif *g_pnetif;
static HANDLE initializer;
static volatile LONG started, result = -100, usable, poll_pending, stopping;
static DWORD previous_poll;

static DWORD WINAPI DP_XboxNetworkWorker(LPVOID unused)
{
    int code;
    (void)unused;
    code = nxNetInit(NULL); /* honor console DHCP/static configuration */
    InterlockedExchange(&result, code);
    return 0;
}

static void DP_XboxReadNetworkState(void *unused)
{
    (void)unused;
    /* Executed on lwIP's tcpip thread, not while DHCP mutates the interface. */
    if (!stopping && g_pnetif)
        InterlockedExchange(&usable, netif_is_up(g_pnetif) &&
            netif_is_link_up(g_pnetif) && !ip4_addr_isany_val(*netif_ip4_addr(g_pnetif)));
    else
        InterlockedExchange(&usable, 0);
    InterlockedExchange(&poll_pending, 0);
}

void DP_XboxNetworkStart(void)
{
    if (InterlockedCompareExchange(&started, 1, 0) != 0) return;
    initializer = CreateThread(NULL, 16384, DP_XboxNetworkWorker, NULL, 0, NULL);
    if (!initializer) InterlockedExchange(&result, -101);
}

void DP_XboxNetworkPoll(void)
{
    DWORD now = GetTickCount();
    LONG code = InterlockedCompareExchange(&result, 0, 0);
    if (stopping || (code != 0 && code != -2)) return;
    /* -2 means initial DHCP timeout, not that the live SDK DHCP service died.
     * Poll it instead of launching a second nxNetInit on cable reconnect. */
    if ((DWORD)(now - previous_poll) < 1000) return;
    previous_poll = now;
    if (InterlockedCompareExchange(&poll_pending, 1, 0) == 0 &&
        tcpip_try_callback(DP_XboxReadNetworkState, NULL) != ERR_OK)
        InterlockedExchange(&poll_pending, 0);
    if (initializer && WaitForSingleObject(initializer, 0) == WAIT_OBJECT_0) {
        CloseHandle(initializer);
        initializer = NULL;
    }
}

int DP_XboxNetworkReady(void) { return InterlockedCompareExchange(&usable, 0, 0) != 0; }
int DP_XboxNetworkResult(void) { return (int)InterlockedCompareExchange(&result, 0, 0); }
void DP_XboxNetworkStop(void)
{
    InterlockedExchange(&stopping, 1);
    InterlockedExchange(&usable, 0);
    /* Engine sockets are closed by LHNET_Shutdown. SDK service lifetime is the
     * XBE lifetime; no unsafe thread termination or pretend teardown. */
    if (initializer) { CloseHandle(initializer); initializer = NULL; }
}
