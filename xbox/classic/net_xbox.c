#include <lwip/sockets.h>
#include <lwip/inet.h>
#include <nxdk/net.h>

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
