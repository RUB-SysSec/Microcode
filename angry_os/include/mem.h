/* memory management
 *   get low address
 *   frame management
 *   paging init 
 *   page fault handler
 *   early kernel heap */

/* credits: wiki.osdev.org, syssec.rub.de */

#pragma once

#include "system.h"
#include "multiboot.h"

typedef struct page {
	unsigned int present:1;
	unsigned int rw:1;
	unsigned int user:1;
	unsigned int writethrough:1;
	unsigned int cachedisable:1;
	unsigned int unused:7;
	unsigned int frame:20;
} __attribute__((packed)) page_t;

typedef struct page_table {
	page_t pages[1024];
} page_table_t;

typedef struct page_directory {
	uintptr_t physical_tables[1024];	/* Physical addresses of the tables */
	page_table_t *tables[1024];	/* 1024 pointers to page tables... */
	uintptr_t physical_address;	/* The physical address of physical_tables */
	int32_t ref_count;
} page_directory_t;

void* mboot_get_low_addr(struct multiboot* mboot);
void set_alloc_start_address(void* start);

void paging_prepare(uint32_t memsize);
void paging_mark_system(uint64_t addr);
void paging_parse_memory_map(uintptr_t mmap_addr, uintptr_t mmap_length);
void paging_install();

void kernel_heap_enable();

void* kmalloc(size_t size);
void* kvmalloc(size_t size);
void* kmalloc_p(size_t size, uintptr_t* phys);
void* kvmalloc_p(size_t size, uintptr_t* phys);