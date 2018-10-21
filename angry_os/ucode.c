/* microcode utility functions
 *   execute x86 payloads
 *	 apply microcode updates
 *   calculate AMD specific microcode checksup */

/* credits: wiki.osdev.org, syssec.rub.de */

#include "system.h"
#include "ucode.h"
#include "libk.h"

uint32_t scratch_space[256];

uint32_t k8_ucode_checksum(k8_ucode_header* hdr) {
	uint32_t* p = (uint32_t*)(&hdr->ucode);
	int i;
	int len = hdr->patch_len * TRIAD_SIZE;
	uint32_t c = 0;
	
	for (i = 0; i < len/4; i++) {
		c += p[i];
	}
	
	return c;
}

uint32_t k8_perform_update(k8_ucode_header* ucode) {
	uint64_t t1, t2;

	t1 = rdtsc();
	wrmsr(MSR_K8_UCODE_UPDATE, (uint32_t)ucode);
	t2 = rdtsc();

	return (uint32_t)(t2 - t1);
}

uint32_t* k8_perform_update_and_call(k8_ucode_header* ucode, fn_t fn) {
	uint64_t t1, t2, t3, t4;

	for(int i = 0; i < 16; i++)
		scratch_space[i] = 0;

	t1 = rdtsc();
	wrmsr(MSR_K8_UCODE_UPDATE, (uint32_t)ucode);
	t2 = rdtsc();

	t3 = rdtsc();
	fn((char*)&scratch_space[2]);
	t4 = rdtsc();

	scratch_space[0] = (uint32_t)(t2 - t1);
	scratch_space[1] = (uint32_t)(t4 - t3);

	return scratch_space;
}

uint32_t* execute_testbench(fn_t fn) {
	uint64_t t1, t2, t3, t4;

	for(int i = 0; i < 16; i++)
		scratch_space[i] = 0;

	t1 = rdtsc();
	//wrmsr(MSR_K8_UCODE_UPDATE, (uint32_t)ucode);
	t2 = rdtsc();

	t3 = rdtsc();
	fn((char*)&scratch_space[2]);
	t4 = rdtsc();

	scratch_space[0] = (uint32_t)(t2 - t1);
	scratch_space[1] = (uint32_t)(t4 - t3);

	return scratch_space;
}