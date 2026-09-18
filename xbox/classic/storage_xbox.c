/* Mount the standard Xbox E: data partition without replacing an existing
 * dashboard or launcher mapping. */

#include <nxdk/mount.h>

#include "include/xbox_storage.h"

int Xbox_MountWritableStorage(void)
{
	if (nxIsDriveMounted('E'))
		return 0;
	return nxMountDrive('E', "\\Device\\Harddisk0\\Partition1\\") ? 0 : -1;
}
