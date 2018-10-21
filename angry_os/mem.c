/* memory management
 *   get low address
 *   frame management
 *   paging init 
 *   page fault handler
 *   early kernel heap */

/* credits: wiki.osdev.org, syssec.rub.de */

#include "system.h"
#include "mem.h"
#include "multiboot.h"
#include "libk.h"
#include "ucsp.h"


#define KERNEL_HEAP_INIT 0x00800000
#define KERNEL_HEAP_END  0x20000000


uintptr_t alloc_address = NULL;
uintptr_t heap_end = NULL;
uintptr_t kernel_heap_alloc_point = KERNEL_HEAP_INIT;

page_directory_t* kernel_directory;


void* mboot_get_low_addr(struct multiboot* mboot) {
	uintptr_t low_addr = 0;
	if(mboot->flags & (1 << 3) && mboot->mods_count > 0) {
		mboot_mod_t* mboot_mods = (mboot_mod_t*)mboot->mods_addr;
		for(uintptr_t i = 0; i < mboot->mods_count; i++) {
			mboot_mod_t* mod = &mboot_mods[i];

			if((uintptr_t)mod + sizeof(mboot_mod_t) > low_addr) {
				low_addr = (uintptr_t)mod + sizeof(mboot_mod_t);
			}

			if (mod->mod_end > low_addr) {
				low_addr = mod->mod_end;
			}
		}
	}
	return (void*)low_addr;
}

void set_alloc_start_address(void* start) {
	alloc_address = (uintptr_t)start;
}

uint32_t *frames;
uint32_t nframes;

#define INDEX_FROM_BIT(b) (b / 0x20)
#define OFFSET_FROM_BIT(b) (b % 0x20)

void set_frame(uintptr_t frame_addr) {
	if (frame_addr < nframes * 4 * 0x400) {
		uint32_t frame  = frame_addr / 0x1000;
		uint32_t index  = INDEX_FROM_BIT(frame);
		uint32_t offset = OFFSET_FROM_BIT(frame);
		frames[index] |= (0x1 << offset);
	}
}

void clear_frame(uintptr_t frame_addr) {
	uint32_t frame  = frame_addr / 0x1000;
	uint32_t index  = INDEX_FROM_BIT(frame);
	uint32_t offset = OFFSET_FROM_BIT(frame);
	frames[index] &= ~(0x1 << offset);
}

uint32_t test_frame(uintptr_t frame_addr) {
	uint32_t frame  = frame_addr / 0x1000;
	uint32_t index  = INDEX_FROM_BIT(frame);
	uint32_t offset = OFFSET_FROM_BIT(frame);
	return (frames[index] & (0x1 << offset));
}

uint32_t first_n_frames(int n) {
	for (uint32_t i = 0; i < nframes * 0x1000; i += 0x1000) {
		int bad = 0;
		for (int j = 0; j < n; ++j) {
			if (test_frame(i + 0x1000 * j)) {
				bad = j+1;
			}
		}
		if (!bad) {
			return i / 0x1000;
		}
	}
	return 0xFFFFFFFF;
}

uint32_t first_frame(void) {
	uint32_t i, j;
	for (i = 0; i < INDEX_FROM_BIT(nframes); ++i) {
		if (frames[i] != 0xFFFFFFFF) {
			for (j = 0; j < 32; ++j) {
				uint32_t testFrame = 0x1 << j;
				if (!(frames[i] & testFrame)) {
					return i * 0x20 + j;
				}
			}
		}
	}
	return 0xFFFFFFFF;
}

void alloc_frame(page_t *page, int is_kernel, int is_writeable) {
	if (page->frame != 0) {
		page->present = 1;
		page->rw      = (is_writeable == 1) ? 1 : 0;
		page->user    = (is_kernel == 1)    ? 0 : 1;
		return;
	} else {
		//spin_lock(frame_alloc_lock);
		uint32_t index = first_frame();
		//assert(index != (uint32_t)-1 && "Out of frames.");
		set_frame(index * 0x1000);
		page->frame   = index;
		//spin_unlock(frame_alloc_lock);
		page->present = 1;
		page->rw      = (is_writeable == 1) ? 1 : 0;
		page->user    = (is_kernel == 1)    ? 0 : 1;
	}
}

void dma_frame(page_t *page, int is_kernel, int is_writeable, uintptr_t address) {
	/* Page this address directly */
	page->present = 1;
	page->rw      = (is_writeable) ? 1 : 0;
	page->user    = (is_kernel)    ? 0 : 1;
	page->frame   = address / 0x1000;
	set_frame(address);
}

void free_frame(page_t *page) {
	uint32_t frame;
	if (!(frame = page->frame)) {
		//assert(0);
		return;
	} else {
		clear_frame(frame * 0x1000);
		page->frame = 0x0;
	}
}

uintptr_t memory_use(void ) {
	uintptr_t ret = 0;
	uint32_t i, j;
	for (i = 0; i < INDEX_FROM_BIT(nframes); ++i) {
		for (j = 0; j < 32; ++j) {
			uint32_t testFrame = 0x1 << j;
			if (frames[i] & testFrame) {
				ret++;
			}
		}
	}
	return ret * 4;
}

uintptr_t memory_total(){
	return nframes * 4;
}

void switch_page_directory(page_directory_t* dir) {
	asm volatile (
			"mov %0, %%cr3\n"
			"mov %%cr0, %%eax\n"
			"orl $0x80000000, %%eax\n"
			"mov %%eax, %%cr0\n"
			:: "r"(dir->physical_address)
			: "%eax");
}

page_t* get_page(uintptr_t address, int make, page_directory_t* dir) {
	address /= 0x1000;
	uint32_t table_index = address / 1024;
	if(dir->tables[table_index]) {
		return &dir->tables[table_index]->pages[address % 1024];
	}
	else if(make) {
		uint32_t temp;
		dir->tables[table_index] = (page_table_t *)kvmalloc_p(sizeof(page_table_t), (uintptr_t *)(&temp));
		memset(dir->tables[table_index], 0, sizeof(page_table_t));
		dir->physical_tables[table_index] = temp | 0x7; /* Present, R/w, User */
		return &dir->tables[table_index]->pages[address % 1024];
	} else {
		return 0;
	}
}

void page_fault(struct regs* r) {
	uint32_t faulting_address;
	asm volatile("mov %%cr2, %0" : "=r"(faulting_address));

	/* send out of order error packet */
	char buf[sizeof(ucsp_header) + sizeof(struct regs) + sizeof(uint32_t)];
	ucsp_header* packet = (ucsp_header*)buf;
	packet->signature = UCSP_SIGNATURE;
	packet->length = sizeof(struct regs) + sizeof(uint32_t);
	packet->type = UCSP_TYPE_OOO_OS_CRASH_R;
	memcpy(buf + sizeof(ucsp_header), r, sizeof(struct regs));
	memcpy(buf + sizeof(ucsp_header) + sizeof(struct regs), &faulting_address, sizeof(uint32_t));
	send_packet(packet);

	/* halt CPU */
	STOP;
}

void paging_prepare(uint32_t memsize) {
	nframes = memsize  / 4;
	frames  = (uint32_t *)kmalloc(INDEX_FROM_BIT(nframes * 8));
	memset(frames, 0, INDEX_FROM_BIT(nframes * 8));

	uintptr_t phys;
	kernel_directory = (page_directory_t *)kvmalloc_p(sizeof(page_directory_t),&phys);
	memset(kernel_directory, 0, sizeof(page_directory_t));
}

void paging_mark_system(uint64_t addr) {
	set_frame(addr);
}

void paging_parse_memory_map(uintptr_t mmap_addr, uintptr_t mmap_length) {
	mboot_memmap_t* mmap = (void*)mmap_addr;
	while((uintptr_t)mmap < mmap_addr + mmap_length) {
		if (mmap->type == 2) {
			for (uint64_t i = 0; i < mmap->length; i += 0x1000) {
				if (mmap->base_addr + i > 0xFFFFFFFF) break;
				paging_mark_system((mmap->base_addr + i) & 0xFFFFF000);
			}
		}
		mmap = (mboot_memmap_t *) ((uintptr_t)mmap + mmap->size + sizeof(uintptr_t));
	}
}

void paging_install() {
	get_page(0,1,kernel_directory)->present = 0;
	set_frame(0);

	for (uintptr_t i = 0x1000; i < 0x80000; i += 0x1000) {
		dma_frame(get_page(i, 1, kernel_directory), 1, 0, i);
	}

	for (uintptr_t i = 0x80000; i < 0x100000; i += 0x1000) {
		dma_frame(get_page(i, 1, kernel_directory), 1, 0, i);
	}

	for (uintptr_t i = 0x100000; i < alloc_address + 0x3000; i += 0x1000) {
		dma_frame(get_page(i, 1, kernel_directory), 1, 0, i);
	}

	for (uintptr_t j = 0xb8000; j < 0xc0000; j += 0x1000) {
		dma_frame(get_page(j, 0, kernel_directory), 0, 1, j);
	}

	isrs_install_handler(14, page_fault);

	kernel_directory->physical_address = (uintptr_t)kernel_directory->physical_tables;

	uintptr_t tmp_heap_start = KERNEL_HEAP_INIT;
	if (tmp_heap_start <= alloc_address + 0x3000) {
		tmp_heap_start = alloc_address + 0x100000;
		kernel_heap_alloc_point = tmp_heap_start;
	}

	for (uintptr_t i = alloc_address + 0x3000; i < tmp_heap_start; i += 0x1000) {
		alloc_frame(get_page(i, 1, kernel_directory), 1, 0);
	}

	for (uintptr_t i = tmp_heap_start; i < KERNEL_HEAP_END; i += 0x1000) {
		get_page(i, 1, kernel_directory);
	}

	switch_page_directory(kernel_directory);
}

void kernel_heap_enable() {
	heap_end = (alloc_address + 0x1000) & ~0xFFF;
}

void* kmalloc_real(size_t size, int align, uintptr_t* phys) {

	/* kernel heap enabled */
	if(heap_end) {

		ucsp_send_ooo_msg("Not implemented reached: kmalloc_real with enabled heap (%d, %d, %x)", size, align, phys);

		return 0;
	}

	/* early alloc */
	if(align && alloc_address & 0xfffff000) {
		alloc_address &= 0xfffff000;
		alloc_address += 0x1000;
	}

	if(phys) {
		*phys = alloc_address;
	}

	void* ret = (void*)alloc_address;
	alloc_address += size;
	return ret;
}

void* kmalloc(size_t size) {
	return kmalloc_real(size, 0, NULL);
}

void* kvmalloc(size_t size) {
	return kmalloc_real(size, 1, NULL);
}

void* kmalloc_p(size_t size, uintptr_t* phys) {
	return kmalloc_real(size, 0, phys);
}

void* kvmalloc_p(size_t size, uintptr_t* phys) {
	return kmalloc_real(size, 1, phys);
}