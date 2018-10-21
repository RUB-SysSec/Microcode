/* simple terminal
 *   navigate, set color
 *   print text, print bmp */

/* credits: wiki.osdev.org, syssec.rub.de */

#pragma once

#include "system.h"

void terminal_initialize(void);

void terminal_setcolor(uint8_t color);
void terminal_setpos(size_t column, size_t row);

void terminal_putchar(char c);
void terminal_write(const char* data, size_t size);
void terminal_writestring(const char* data);
int terminal_printf(const char* fmt, ...);

void terminal_drawbmp(uint8_t* data);