/* simple terminal
 *   navigate, set color
 *   print text, print bmp */

/* credits: wiki.osdev.org, syssec.rub.de */

#include "system.h"
#include "tty.h"
#include "libk.h"
#include "vga.h"
#include "bmp.h"

size_t terminal_row;
size_t terminal_column;
uint8_t terminal_color;

void terminal_initialize(void) {
	terminal_row = 0;
	terminal_column = 0;
	terminal_color = vga_entry_color(VGA_COLOR_LIGHT_GREY, VGA_COLOR_BLACK);
	for (size_t y = 0; y < VGA_HEIGHT; y++) {
		for (size_t x = 0; x < VGA_WIDTH; x++) {
			const size_t index = y * VGA_WIDTH + x;
			VGA_MEMORY[index] = vga_entry(' ', terminal_color);
		}
	}
}

void terminal_setcolor(uint8_t color) {
	terminal_color = color;
}

void terminal_setpos(size_t column, size_t row) {
	terminal_column = column;
	terminal_row = row;
}

void terminal_putentryat(char c, uint8_t color, size_t x, size_t y) {
	const size_t index = y * VGA_WIDTH + x;
	VGA_MEMORY[index] = vga_entry(c, color);
}

void terminal_scroll() {
	for(size_t y = 1; y < VGA_HEIGHT; y++) {
		for(size_t x = 0; x < VGA_WIDTH; x++) {
			VGA_MEMORY[(y - 1) * VGA_WIDTH + x] = VGA_MEMORY[y * VGA_WIDTH + x];
		}
	}

	uint16_t entry = vga_entry(' ', vga_entry_color(VGA_COLOR_LIGHT_GREY, VGA_COLOR_BLACK));
	for(size_t x = 0; x < VGA_WIDTH; x++) {
		VGA_MEMORY[(VGA_HEIGHT - 1) * VGA_WIDTH + x] = entry;
	}

	terminal_row = VGA_HEIGHT - 1;
}

void terminal_putchar(char c) {
	if(c == '\n') {
		terminal_column = 0;
		if(++terminal_row == VGA_HEIGHT)
			terminal_scroll();
	}
	else {
		terminal_putentryat(c, terminal_color, terminal_column, terminal_row);
		if (++terminal_column == VGA_WIDTH) {
			terminal_column = 0;
			if (++terminal_row == VGA_HEIGHT)
				terminal_scroll();
		}
	}
}

void terminal_write(const char* data, size_t size) {
	for (size_t i = 0; i < size; i++)
		terminal_putchar(data[i]);
}

void terminal_writestring(const char* data) {
	terminal_write(data, strlen(data));
}

int terminal_printf(const char* fmt, ...) {
	char buf[1024];
	va_list args;
	va_start(args, fmt);
	int out = vasprintf(buf, fmt, args);
	va_end(args);
	terminal_writestring(buf);
	return out;
}

void terminal_drawbmp(uint8_t* data) {
	BITMAPFILEHEADER* file_header = (BITMAPFILEHEADER*)data;
	BITMAPINFOHEADER* info_header = (BITMAPINFOHEADER*)(data + sizeof(BITMAPFILEHEADER));

	if(file_header->bfType != 0x4D42) {
		terminal_setcolor(vga_entry_color(VGA_COLOR_RED, VGA_COLOR_BLACK));
		terminal_writestring("Invalid Bitmap!\n");
		return;
	}

	if((uint32_t)info_header->biWidth > VGA_WIDTH) {
		terminal_setcolor(vga_entry_color(VGA_COLOR_RED, VGA_COLOR_BLACK));
		terminal_writestring("Bitmap too large!\n");
		return;
	}

	if(info_header->biClrUsed != 16) {
		terminal_setcolor(vga_entry_color(VGA_COLOR_RED, VGA_COLOR_BLACK));
		terminal_writestring("Unsupported color profile!\n");
		return;
	}

	uint8_t* pixels = (uint8_t*)(data + file_header->bOffBits);

	int row_bits = info_header->biWidth * info_header->biBitCount;
	row_bits = row_bits % 32 == 0 ? row_bits : row_bits + 32 - row_bits % 32;
	int row_bytes = row_bits / 8;

	int x, y;
	for(x = 0; x < info_header->biWidth; x += 2) {
		for(y = 0; y < info_header->biHeight / 2; y++) {
			int index = (info_header->biHeight - 2 - y * 2) * row_bytes + (x >> 1);
			uint8_t upper_pixel = pixels[index];
			index = (info_header->biHeight - 1 - y * 2) * row_bytes + (x >> 1);
			uint8_t lower_pixel = pixels[index];

			terminal_putentryat('\xdc', vga_entry_color(upper_pixel >> 4, lower_pixel >> 4), x + 1, y);
			terminal_putentryat('\xdc', vga_entry_color(upper_pixel & 0x0f, lower_pixel & 0x0f), x + 2, y);
		}
	}
}