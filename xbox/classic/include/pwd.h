#ifndef XBOX_CLASSIC_PWD_H
#define XBOX_CLASSIC_PWD_H
#include <sys/types.h>
struct passwd { char *pw_name; char *pw_dir; };
static inline struct passwd *getpwuid(unsigned int uid)
{
	(void)uid;
	return (struct passwd *)0;
}
#ifndef getuid
#define getuid() 0
#endif
#endif
