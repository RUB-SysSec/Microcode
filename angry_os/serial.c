/* serial communication utility functions
 *   init
 *   receive/send
 *   blocking/unblocking */

/* credits: wiki.osdev.org, syssec.rub.de */

#include "system.h"
#include "serial.h"
#include "libk.h"

void serial_enable(int device) {
	outportb(device + 1, 0x00);
	outportb(device + 3, 0x80); /* Enable divisor mode */
	outportb(device + 0, 0x03); /* Div Low:  03 Set the port to 38400 baud */
	outportb(device + 1, 0x00); /* Div High: 00 */
	outportb(device + 3, 0x03); /* 8 bits, no parity, one stop bit */
	outportb(device + 2, 0xC7);
	outportb(device + 4, 0x0B);
}

int serial_rcvd(int device) {
	return inportb(device + 5) & 1;
}

char serial_recv(int device) {
	while (serial_rcvd(device) == 0) ;
	return inportb(device);
}

int serial_recv_string(int device, char* buf, int size) {
	if(size == 0)
		return 0;

	int pos = 0;
	while(1) {
		char c = serial_recv(device);
		buf[pos] = c;
		pos++;

		if(c == 0 || c == '\n' || pos >= size)
			return pos;

	}
}

char serial_recv_async(int device) {
	return inportb(device);
}

int serial_transmit_empty(int device) {
	return inportb(device + 5) & 0x20;
}

void serial_send(int device, char out) {
	while (serial_transmit_empty(device) == 0);
	outportb(device, out);
}

void serial_send_string(int device, char * out) {
	for (uint32_t i = 0; i < strlen(out); ++i) {
		serial_send(device, out[i]);
	}
}

int serial_printf(int device, const char* fmt, ...) {
	char buf[1024];
	va_list args;
	va_start(args, fmt);
	int out = vasprintf(buf, fmt, args);
	va_end(args);
	serial_send_string(device, buf);
	return out;
}