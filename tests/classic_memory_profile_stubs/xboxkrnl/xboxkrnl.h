#ifndef TEST_XBOXKRNL_H
#define TEST_XBOXKRNL_H

#include <stdint.h>

#define PAGE_SIZE 4096

typedef int32_t NTSTATUS;
typedef uint32_t ULONG;

typedef struct _MM_STATISTICS
{
	ULONG Length;
	ULONG TotalPhysicalPages;
	ULONG AvailablePages;
	ULONG VirtualMemoryBytesCommitted;
	ULONG VirtualMemoryBytesReserved;
	ULONG CachePagesCommitted;
	ULONG PoolPagesCommitted;
	ULONG StackPagesCommitted;
	ULONG ImagePagesCommitted;
} MM_STATISTICS, *PMM_STATISTICS;

NTSTATUS MmQueryStatistics(PMM_STATISTICS statistics);

#endif
