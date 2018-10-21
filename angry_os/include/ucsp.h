/* simple communication protocol
 *   used over serial
 *   used to send microcode and x86 code payloads */

/* credits: wiki.osdev.org, syssec.rub.de */

#pragma once

#include "system.h"

#pragma pack(push, 1)
typedef struct {
	uint32_t signature;
	uint16_t type;
	uint16_t length;
	
	uint8_t payload[];
} ucsp_header;
#pragma pack(pop)

#define UCSP_SIGNATURE 0xefbeadde

#define UCSP_TYPE_PING 1
#define UCSP_TYPE_PONG 2
#define UCSP_TYPE_CPUID 3
#define UCSP_TYPE_CPUID_R 4
#define UCSP_TYPE_SET_UCODE 5
#define UCSP_TYPE_SET_UCODE_R 6
#define UCSP_TYPE_PATCH_UCODE 7
#define UCSP_TYPE_PATCH_UCODE_R 8
#define UCSP_TYPE_APPLY_UCODE 9
#define UCSP_TYPE_APPLY_UCODE_R 10
#define UCSP_TYPE_EXECUTE_CODE 11
#define UCSP_TYPE_EXECUTE_CODE_R 12
#define UCSP_TYPE_OOO_OS_CRASH_R 14
#define UCSP_TYPE_OOO_MSG_R 16
#define UCSP_TYPE_EXECUTE_CODE_NOUPDATE 18

#define UCSP_MAX_LEN (1024 * 50)

int assemble_packet(uint8_t* buf, unsigned int length);
void dispatch_packet(ucsp_header* packet);
void send_packet(ucsp_header* packet);

void ucsp_set_device(int device);
int ucsp_get_device();

void ucsp_enter_packet_loop();

void ucsp_send_ooo_msg(const char* fmt, ...);