/* GDT
 *   structs
 *   setup */

/* credits: wiki.osdev.org, syssec.rub.de */

#include <system.h>

typedef struct {
	/* Limits */
	uint16_t limit_low;
	/* Segment address */
	uint16_t base_low;
	uint8_t base_middle;
	/* Access modes */
	uint8_t access;
	uint8_t granularity;
	uint8_t base_high;
} __attribute__((packed)) gdt_entry_t;

typedef struct {
	uint16_t limit;
	uintptr_t base;
} __attribute__((packed)) gdt_pointer_t;

/* In the future we may need to put a lock on the access of this */
static struct {
    gdt_entry_t entries[6];
    gdt_pointer_t pointer;
} gdt __attribute__((used));

extern void gdt_flush(uintptr_t);

#define ENTRY(X) (gdt.entries[(X)])

void gdt_set_gate(uint8_t num, uint64_t base, uint64_t limit, uint8_t access, uint8_t gran) {
	/* Base Address */
	ENTRY(num).base_low = (base & 0xFFFF);
	ENTRY(num).base_middle = (base >> 16) & 0xFF;
	ENTRY(num).base_high = (base >> 24) & 0xFF;
	/* Limits */
	ENTRY(num).limit_low = (limit & 0xFFFF);
	ENTRY(num).granularity = (limit >> 16) & 0X0F;
	/* Granularity */
	ENTRY(num).granularity |= (gran & 0xF0);
	/* Access flags */
	ENTRY(num).access = access;
}

void gdt_install(void) {
	gdt_pointer_t *gdtp = &gdt.pointer;
	gdtp->limit = sizeof gdt.entries - 1;
	gdtp->base = (uintptr_t)&ENTRY(0);

	gdt_set_gate(0, 0, 0, 0, 0);                /* NULL segment */
	gdt_set_gate(1, 0, 0xFFFFFFFF, 0x9A, 0xCF); /* Code segment */
	gdt_set_gate(2, 0, 0xFFFFFFFF, 0x92, 0xCF); /* Data segment */
	gdt_set_gate(3, 0, 0xFFFFFFFF, 0xFA, 0xCF); /* User code */
	gdt_set_gate(4, 0, 0xFFFFFFFF, 0xF2, 0xCF); /* User data */

	gdt_flush((uintptr_t)gdtp);
}