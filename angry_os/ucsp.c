/* simple communication protocol
 *   used over serial
 *   used to send microcode and x86 code payloads */

/* credits: wiki.osdev.org, syssec.rub.de */

#include "system.h"
#include "ucsp.h"
#include "serial.h"
#include "libk.h"
#include "ucode.h"

uint8_t ucsp_sig[4] = {0xDE, 0xAD, 0xBE, 0xEF};

uint8_t packet_buf_in[UCSP_MAX_LEN];
uint8_t packet_buf_out[UCSP_MAX_LEN];

uint8_t ucode_mem[UCSP_MAX_LEN];

bool is_code_installed = false;
uint8_t exec_code[UCSP_MAX_LEN];

int ucsp_device = 0;

void ucsp_set_device(int device) {
	ucsp_device = device;
}

int ucsp_get_device() {
	return ucsp_device;
}

void ucsp_enter_packet_loop() {
	while(1) {
		if(assemble_packet(packet_buf_in, UCSP_MAX_LEN)) {
			dispatch_packet((ucsp_header*) packet_buf_in);
		}
	}
}

int assemble_packet(uint8_t* buf, unsigned int length) {
	uint8_t c;
	unsigned int i = 0;
	ucsp_header* hdr = (ucsp_header*) buf;

	while(1) {
		c = (uint8_t)serial_recv(ucsp_device);

		/* look for header */
		if(i < sizeof(hdr->signature)) {
			if(c == ucsp_sig[i]) {
				buf[i] = c;
				i++;
			}
			else {
				i = 0;
			}
		}

		/* get entire header */
		else if(i < sizeof(ucsp_header) ) {
			buf[i] = c;

			/* dispatch complete packet */
			if(i == sizeof(ucsp_header) - 1 && hdr->length == 0) {
				return sizeof(ucsp_header);
			}

			i++;
		}

		/* get entire packet */
		else if(i < sizeof(ucsp_header) + hdr->length) {
			buf[i] = c;

			/* check for too large packet */
			if(length < sizeof(ucsp_header) + hdr->length) {
				return 0;
			}

			/* dispatch complete packet */
			if(i == sizeof(ucsp_header) + hdr->length - 1) {
				return sizeof(ucsp_header) + hdr->length;
			}

			i++;
		}
	}

	return 0;
}

void dispatch_packet(ucsp_header* packet) {
	ucsp_header* packet_out = (ucsp_header*) packet_buf_out;

	if(packet->type == UCSP_TYPE_PING) {
		for(unsigned int i = 0; i < sizeof(ucsp_header) + packet->length; i++) {
			packet_buf_out[i] = ((char*)packet)[i];
		}
		packet_out->type = UCSP_TYPE_PONG;
		send_packet(packet_out);
	}

	else if(packet->type == UCSP_TYPE_CPUID) {
		packet_out->signature = packet->signature;
		packet_out->type = UCSP_TYPE_CPUID_R;

		char* cpuid_str = dump_cpuid();
		size_t len = strlen(cpuid_str);

		memcpy(packet_buf_out + sizeof(ucsp_header), cpuid_str, len + 1);

		packet_out->length = len + 1;
		send_packet(packet_out);
	}

	else if(packet->type == UCSP_TYPE_SET_UCODE) {
		memcpy(ucode_mem, packet_buf_in + sizeof(ucsp_header), packet->length);
		packet_out->signature = packet->signature;
		packet_out->type = UCSP_TYPE_SET_UCODE_R;
		packet_out->length = 0;
		send_packet(packet_out);
	}

	else if(packet->type == UCSP_TYPE_PATCH_UCODE) {
		if(packet->length == 8) {
			uint32_t offset = *(uint32_t*)(packet_buf_in + sizeof(ucsp_header));
			uint32_t value = *(uint32_t*)(packet_buf_in + sizeof(ucsp_header) + sizeof(uint32_t));

			if(offset <= UCSP_MAX_LEN - sizeof(uint32_t)) {
				*(uint32_t*)(ucode_mem + offset) = value;

				packet_out->signature = packet->signature;
				packet_out->type = UCSP_TYPE_PATCH_UCODE_R;
				packet_out->length = 0;
				send_packet(packet_out);
			}
		}
	}

	else if(packet->type == UCSP_TYPE_APPLY_UCODE) {
		if(is_code_installed) {
			uint32_t* ret = k8_perform_update_and_call((k8_ucode_header*) ucode_mem, (fn_t) exec_code);
			packet_out->length = 64 * sizeof(uint32_t);
			memcpy(packet_buf_out + sizeof(ucsp_header), ret, 64 * sizeof(uint32_t));
		}
		else {
			uint32_t ticks = k8_perform_update((k8_ucode_header*) ucode_mem);
			packet_out->length = 4;
			*(uint32_t*)(packet_buf_out + sizeof(ucsp_header)) = ticks;
		}

		packet_out->signature = packet->signature;
		packet_out->type = UCSP_TYPE_APPLY_UCODE_R;
		send_packet(packet_out);
	}

	else if(packet->type == UCSP_TYPE_EXECUTE_CODE) {
		if(packet->length == 0) {
			is_code_installed = false;
		}
		else {
			memcpy(exec_code, packet_buf_in + sizeof(ucsp_header), packet->length);
			is_code_installed = true;
		}
		packet_out->signature = packet->signature;
		packet_out->type = UCSP_TYPE_EXECUTE_CODE_R;
		packet_out->length = 0;
		send_packet(packet_out);
	}
	else if(packet->type == UCSP_TYPE_EXECUTE_CODE_NOUPDATE) {
		uint32_t* ret = execute_testbench((fn_t) exec_code);
		packet_out->length = 64 * sizeof(uint32_t);
		memcpy(packet_buf_out + sizeof(ucsp_header), ret, 64 * sizeof(uint32_t));
		packet_out->signature = packet->signature;
		packet_out->type = UCSP_TYPE_APPLY_UCODE_R;
		send_packet(packet_out);
	}
}

void send_packet(ucsp_header* packet) {
	unsigned int len = sizeof(ucsp_header) + packet->length;
	for(unsigned int i = 0; i < len; i++) {
		serial_send(ucsp_device, ((char*)packet)[i]);
	}
}

void ucsp_send_ooo_msg(const char* fmt, ...) {
	char buf[sizeof(ucsp_header) + 1000]; //fixme: use heap allocator later

	char* str = buf + sizeof(ucsp_header);
	va_list args;
	va_start(args, fmt);
	size_t len = vasprintf(str, fmt, args);
	va_end(args);

	ucsp_header* packet = (ucsp_header*)buf;
	packet->signature = UCSP_SIGNATURE;
	packet->length = (uint16_t)len;
	packet->type = UCSP_TYPE_OOO_MSG_R;

	send_packet(packet);
}