/* minimal kernel libc
 *   format print to string
 *   strlen/memcpy/memset
 *   cpuid */

/* credits: wiki.osdev.org, syssec.rub.de */

#include "system.h"
#include "libk.h"

static void print_dec(unsigned int value, unsigned int width, char * buf, int * ptr ) {
	unsigned int n_width = 1;
	unsigned int i = 9;
	while (value > i && i < UINT32_MAX) {
		n_width += 1;
		i *= 10;
		i += 9;
	}

	int printed = 0;
	while (n_width + printed < width) {
		buf[*ptr] = '0';
		*ptr += 1;
		printed += 1;
	}

	i = n_width;
	while (i > 0) {
		unsigned int n = value / 10;
		int r = value % 10;
		buf[*ptr + i - 1] = r + '0';
		i--;
		value = n;
	}
	*ptr += n_width;
}

static void print_hex(unsigned int value, unsigned int width, char * buf, int * ptr) {
	int i = width;

	if (i == 0) i = 8;

	unsigned int n_width = 1;
	unsigned int j = 0x0F;
	while (value > j && j < UINT32_MAX) {
		n_width += 1;
		j *= 0x10;
		j += 0x0F;
	}

	while (i > (int)n_width) {
		buf[*ptr] = '0';
		*ptr += 1;
		i--;
	}

	i = (int)n_width;
	while (i-- > 0) {
		buf[*ptr] = "0123456789abcdef"[(value>>(i*4))&0xF];
		*ptr += + 1;
	}
}

size_t vasprintf(char * buf, const char *fmt, va_list args) {
	int i = 0;
	char *s;
	int ptr = 0;
	int len = strlen(fmt);
	for ( ; i < len && fmt[i]; ++i) {
		if (fmt[i] != '%') {
			buf[ptr++] = fmt[i];
			continue;
		}
		++i;
		unsigned int arg_width = 0;
		while (fmt[i] >= '0' && fmt[i] <= '9') {
			arg_width *= 10;
			arg_width += fmt[i] - '0';
			++i;
		}
		/* fmt[i] == '%' */
		switch (fmt[i]) {
			case 's': /* String pointer -> String */
				s = (char *)va_arg(args, char *);
				while (*s) {
					buf[ptr++] = *s++;
				}
				break;
			case 'c': /* Single character */
				buf[ptr++] = (char)va_arg(args, int);
				break;
			case 'x': /* Hexadecimal number */
				print_hex((unsigned long)va_arg(args, unsigned long), arg_width, buf, &ptr);
				break;
			case 'd': /* Decimal number */
				print_dec((unsigned long)va_arg(args, unsigned long), arg_width, buf, &ptr);
				break;
			case '%': /* Escape */
				buf[ptr++] = '%';
				break;
			default: /* Nothing at all, just dump it */
				buf[ptr++] = fmt[i];
				break;
		}
	}
	/* Ensure the buffer ends in a null */
	buf[ptr] = '\0';
	return ptr;
}

int sprintf(char * buf, const char *fmt, ...) {
	va_list args;
	va_start(args, fmt);
	int out = vasprintf(buf, fmt, args);
	va_end(args);
	return out;
}

size_t strlen(const char* str) {
	size_t len = 0;
	while (str[len])
		len++;
	return len;
}

void memcpy(void* dst, void* src, size_t len) {
	for(size_t i = 0; i < len; i++) {
		((char*)dst)[i] = ((char*)src)[i];
	}
}

void* memset(void* dst, int c, size_t len) {
	for(size_t i = 0; i < len; i++) {
		((char*)dst)[i] = (char)c;
	}
	return dst;
}

char buf[1024];
char* dump_cpuid() {
	unsigned int eax, ebx, ecx, edx;
	
	__get_cpuid(0, &eax, &ebx, &ecx, &edx);

	unsigned int highest_function = eax;

	char vendor[16] = {0};
	vendor[0] = ebx & 0xFF;
	vendor[1] = (ebx >> 8) & 0xFF;
	vendor[2] = (ebx >> 16) & 0xFF;
	vendor[3] = (ebx >> 24) & 0xFF;

	vendor[4] = edx & 0xFF;
	vendor[5] = (edx >> 8) & 0xFF;
	vendor[6] = (edx >> 16) & 0xFF;
	vendor[7] = (edx >> 24) & 0xFF;

	vendor[8] = ecx & 0xFF;
	vendor[9] = (ecx >> 8) & 0xFF;
	vendor[10] = (ecx >> 16) & 0xFF;
	vendor[11] = (ecx >> 24) & 0xFF;

	__get_cpuid(1, &eax, &ebx, &ecx, &edx);

	unsigned int cpuid, stepping, model, family, type, extmodel, extfamily;

	cpuid = eax;
	stepping = eax & 0xF;
	model = (eax >> 4) & 0xF;
	family = (eax >> 8) & 0xF;
	type = (eax >> 12) & 0x3;
	extmodel = (eax >> 16) & 0xF;
	extfamily = (eax >> 20) & 0xFF;


	sprintf(buf,	"Highest function: %d\n"
					"Vendor string: %s\n"
					"CPUID: 0x%x -->\n"
					"    type=%d family=%d model=%d stepping=%d extfam=%d extmodel=%d\n",
					highest_function, vendor, cpuid,
					type, family, model, stepping, extfamily, extmodel);

	return buf;
}

int raise_gpf()
{
	return *(uint32_t*)(0);
}
