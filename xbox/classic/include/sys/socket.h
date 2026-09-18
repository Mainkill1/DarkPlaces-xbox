#ifndef XBOX_CLASSIC_SYS_SOCKET_H
#define XBOX_CLASSIC_SYS_SOCKET_H
#include <lwip/sockets.h>
#include <xbox_network.h>

/* nxNetInit runs on a bounded background thread so offline startup cannot wait
 * for DHCP.  Do not enter lwIP before that thread has initialized tcpip. */
#undef socket
#define socket(domain,type,protocol) Xbox_NetworkSocket((domain),(type),(protocol))
#endif
