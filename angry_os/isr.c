/* ISR
 *   setup
 *   generic handler
 *   exception number to string table */

/* credits: wiki.osdev.org, syssec.rub.de */

#include "system.h"

/*
 * Exception Handlers
 */
extern void _isr0();
extern void _isr1();
extern void _isr2();
extern void _isr3();
extern void _isr4();
extern void _isr5();
extern void _isr6();
extern void _isr7();
extern void _isr8();
extern void _isr9();
extern void _isr10();
extern void _isr11();
extern void _isr12();
extern void _isr13();
extern void _isr14();
extern void _isr15();
extern void _isr16();
extern void _isr17();
extern void _isr18();
extern void _isr19();
extern void _isr20();
extern void _isr21();
extern void _isr22();
extern void _isr23();
extern void _isr24();
extern void _isr25();
extern void _isr26();
extern void _isr27();
extern void _isr28();
extern void _isr29();
extern void _isr30();
extern void _isr31();
extern void _isr127();

static irq_handler_t isr_routines[256] = { 0 };

void isrs_install_handler(size_t isrs, irq_handler_t handler) {
	isr_routines[isrs] = handler;
}

void isrs_uninstall_handler(size_t isrs) {
	isr_routines[isrs] = 0;
}

void isrs_install(void) {

	/* Exception Handlers */
	idt_set_gate(0, (void*)_isr0, 0x08, 0x8E);
	idt_set_gate(1, (void*)_isr1, 0x08, 0x8E);
	idt_set_gate(2, (void*)_isr2, 0x08, 0x8E);
	idt_set_gate(3, (void*)_isr3, 0x08, 0x8E);
	idt_set_gate(4, (void*)_isr4, 0x08, 0x8E);
	idt_set_gate(5, (void*)_isr5, 0x08, 0x8E);
	idt_set_gate(6, (void*)_isr6, 0x08, 0x8E);
	idt_set_gate(7, (void*)_isr7, 0x08, 0x8E);
	idt_set_gate(8, (void*)_isr8, 0x08, 0x8E);
	idt_set_gate(9, (void*)_isr9, 0x08, 0x8E);
	idt_set_gate(10, (void*)_isr10, 0x08, 0x8E);
	idt_set_gate(11, (void*)_isr11, 0x08, 0x8E);
	idt_set_gate(12, (void*)_isr12, 0x08, 0x8E);
	idt_set_gate(13, (void*)_isr13, 0x08, 0x8E);
	idt_set_gate(14, (void*)_isr14, 0x08, 0x8E);
	idt_set_gate(15, (void*)_isr15, 0x08, 0x8E);
	idt_set_gate(16, (void*)_isr16, 0x08, 0x8E);
	idt_set_gate(17, (void*)_isr17, 0x08, 0x8E);
	idt_set_gate(18, (void*)_isr18, 0x08, 0x8E);
	idt_set_gate(19, (void*)_isr19, 0x08, 0x8E);
	idt_set_gate(20, (void*)_isr20, 0x08, 0x8E);
	idt_set_gate(21, (void*)_isr21, 0x08, 0x8E);
	idt_set_gate(22, (void*)_isr22, 0x08, 0x8E);
	idt_set_gate(23, (void*)_isr23, 0x08, 0x8E);
	idt_set_gate(24, (void*)_isr24, 0x08, 0x8E);
	idt_set_gate(25, (void*)_isr25, 0x08, 0x8E);
	idt_set_gate(26, (void*)_isr26, 0x08, 0x8E);
	idt_set_gate(27, (void*)_isr27, 0x08, 0x8E);
	idt_set_gate(28, (void*)_isr28, 0x08, 0x8E);
	idt_set_gate(29, (void*)_isr29, 0x08, 0x8E);
	idt_set_gate(30, (void*)_isr30, 0x08, 0x8E);
	idt_set_gate(31, (void*)_isr31, 0x08, 0x8E);
	idt_set_gate(SYSCALL_VECTOR, (void*)_isr127, 0x08, 0x8E);
}

const char *exception_messages[32] = {
	"Division by zero",
	"Debug",
	"Non-maskable interrupt",
	"Breakpoint",
	"Detected overflow",
	"Out-of-bounds",
	"Invalid opcode",
	"No coprocessor",
	"Double fault",
	"Coprocessor segment overrun",
	"Bad TSS",
	"Segment not present",
	"Stack fault",
	"General protection fault",
	"Page fault",
	"Unknown interrupt",
	"Coprocessor fault",
	"Alignment check",
	"Machine check",
	"Reserved",
	"Reserved",
	"Reserved",
	"Reserved",
	"Reserved",
	"Reserved",
	"Reserved",
	"Reserved",
	"Reserved",
	"Reserved",
	"Reserved",
	"Reserved",
	"Reserved"
};

void fault_handler(struct regs * r) {
	irq_handler_t handler = isr_routines[r->int_no];
	if (handler) {
		handler(r);
	} else {
		STOP;
	}
}