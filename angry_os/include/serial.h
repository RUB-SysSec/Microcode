/* serial communication utility functions
 *   init
 *   receive/send
 *   blocking/unblocking */

/* credits: wiki.osdev.org, syssec.rub.de */

#pragma once

#include "system.h"

#define SERIAL_PORT_A 0x3F8
#define SERIAL_PORT_B 0x2F8
#define SERIAL_PORT_C 0x3E8
#define SERIAL_PORT_D 0x2E8

void serial_enable(int device);

int serial_rcvd(int device);
char serial_recv(int device);
char serial_recv_async(int device);
int serial_recv_string(int device, char* buf, int size);

int serial_transmit_empty(int device);
void serial_send(int device, char out);
void serial_send_string(int device, char * out);
int serial_printf(int device, const char* fmt, ...);