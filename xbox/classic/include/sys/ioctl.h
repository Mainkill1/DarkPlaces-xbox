#ifndef XBOX_CLASSIC_SYS_IOCTL_H
#define XBOX_CLASSIC_SYS_IOCTL_H
#include <lwip/sockets.h>
#ifndef ioctl
#define ioctl(s,cmd,argp) lwip_ioctl((s),(cmd),(argp))
#endif
#endif
