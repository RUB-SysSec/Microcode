/* microcode utility functions
 *   execute x86 payloads
 *	 apply microcode updates
 *   calculate AMD specific microcode checksup */

/* credits: wiki.osdev.org, syssec.rub.de */

#pragma once

#include "system.h"

typedef void (*fn_t)(char* scratch_space);

#pragma pack(push, 1)
typedef struct {
	uint32_t creation_date;
	uint32_t patch_id;
	uint16_t mpb_id;
	uint8_t patch_len;
	uint8_t init_flag;
	uint32_t checksum;

	uint32_t uk0;
	uint32_t uk1;
	uint32_t cpuid;
	uint32_t signature;
	
	uint32_t match_register[8];
	
	uint8_t ucode[];
} k8_ucode_header;
#pragma pack(pop)

#define TRIAD_SIZE 28
#define MSR_K8_UCODE_UPDATE 0xc0010020

uint32_t k8_ucode_checksum(k8_ucode_header* ucode);
uint32_t k8_perform_update(k8_ucode_header* ucode);
uint32_t* k8_perform_update_and_call(k8_ucode_header* ucode, fn_t fn);
uint32_t* execute_testbench(fn_t fn);