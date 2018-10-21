/* angry os minimal kernel
 *   default ISR handler
 *   kernel entry and early init
 *   welcome message
 *   serial communication loop */

/* credits: wiki.osdev.org, syssec.rub.de */

#include "system.h"
#include "libk.h"
#include "multiboot.h"
#include "serial.h"
#include "ucsp.h"
#include "mem.h"
#include "vga.h"
#include "tty.h"
#include "logo/logo.h"

//#define SERIAL_DISABLE

#ifdef SERIAL_DISABLE
#include "ucode.h"
#include "patches/600f12.h"
#endif

/* Check if the compiler thinks we are targeting the wrong operating system. */
#if defined(__linux__)
#error "You are not using a cross-compiler, you will most certainly run into trouble"
#endif

/* This kernel will only work for the 32-bit ix86 targets. */
#if !defined(__i386__)
#error "This kernel needs to be compiled with a ix86-elf compiler"
#endif

void flip_bit(char* buf, int pos)
{
	int byte = pos / 8;
	int bit = pos % 8;
	buf[byte] ^= 1 << bit;
}

void isr_handler(struct regs* r) {

#ifndef SERIAL_DISABLE
	/* send out of order error packet */
	char buf[sizeof(ucsp_header) + sizeof(struct regs)];
	ucsp_header* packet = (ucsp_header*)buf;
	packet->signature = UCSP_SIGNATURE;
	packet->length = sizeof(struct regs);
	packet->type = UCSP_TYPE_OOO_OS_CRASH_R;
	memcpy(buf + sizeof(ucsp_header), r, sizeof(struct regs));
	send_packet(packet);
#else
	terminal_printf("CPU crashed with int %d and error code %d.\n", r->int_no, r->err_code);
	terminal_printf("Faulting EIP 0x%x.\n", r->eip);
#endif

	/* halt CPU */
	STOP;
}

void kernel_main(struct multiboot *mboot, uint32_t mboot_mag, uintptr_t esp) {
	UNUSED(mboot_mag);
	UNUSED(esp);


	/* setup ISRs */
	gdt_install();
	idt_install();
	isrs_install();


	/* install default handler for ISRs */
	for(size_t i = 0; i < 32; i++) {
		isrs_install_handler(i, isr_handler);
	}
	isrs_install_handler(SYSCALL_VECTOR, isr_handler);


	/* setup memory management */
	void* low_addr = mboot_get_low_addr(mboot);
	if((uintptr_t)&end > (uintptr_t)low_addr) {
		low_addr = &end;
	}
	set_alloc_start_address(low_addr);


	/* enable paging */
	paging_prepare(mboot->mem_upper + mboot->mem_lower);
	if(mboot->flags & (1 << 6)) {
		paging_parse_memory_map(mboot->mmap_addr, mboot->mmap_length);
	}
	paging_install();


	/* enable kernel heap */
	//kernel_heap_enable();


	/* enable serial port A */
#ifndef SERIAL_DISABLE
	serial_enable(SERIAL_PORT_A);
#endif


	/* bind ucsp to serial port A */
#ifndef SERIAL_DISABLE
	ucsp_set_device(SERIAL_PORT_A);
#endif


	/* initialize terminal interface */
	terminal_initialize();


	/* draw splash screen */
	terminal_drawbmp(logo);
	terminal_setcolor(vga_entry_color(VGA_COLOR_BLACK, VGA_COLOR_RED));
	terminal_setpos(19, 9);
	terminal_writestring("Angry OS");
	terminal_setpos(0, 24);
	terminal_setcolor(vga_entry_color(VGA_COLOR_LIGHT_GREY, VGA_COLOR_BLACK));

#ifdef SERIAL_DISABLE

	terminal_printf("Hello world\n");

	volatile uint8_t volatile * volatile patch = kmalloc(patch_600f12_size);
	memcpy(patch, patch_600f12, patch_600f12_size);

	uint64_t t1, t2;

	for(int i = 0; i < 200; i++) {

		flip_bit((char*)patch, i);

		t1 = rdtsc();
		wrmsr(MSR_K8_UCODE_UPDATE, (uint32_t)patch);
		t2 = rdtsc();

		flip_bit((char*)patch, i);

		terminal_printf("%d ", (uint32_t)(t2 - t1));

		for(volatile int j = 0; j < 5000000; j++) {
		}

	}

#endif


	/* start listening for packets */
#ifndef SERIAL_DISABLE
	ucsp_enter_packet_loop();
#endif
}