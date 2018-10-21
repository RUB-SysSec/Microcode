/* minimal kernel libc
 *   format print to string
 *   strlen/memcpy/memset
 *   cpuid */

/* credits: wiki.osdev.org, syssec.rub.de */

#pragma once

#include "system.h"
#include "cpuid.h"

typedef __builtin_va_list va_list;
#define va_start(ap,last) __builtin_va_start(ap, last)
#define va_end(ap) __builtin_va_end(ap)
#define va_arg(ap,type) __builtin_va_arg(ap,type)
#define va_copy(dest, src) __builtin_va_copy(dest,src)

size_t vasprintf(char * buf, const char *fmt, va_list args);
int sprintf(char * buf, const char *fmt, ...);

size_t strlen(const char* str);
void memcpy(void* dst, void* src, size_t len);
void* memset(void* dst, int c, size_t len);

char* dump_cpuid();
int raise_gpf();

static inline uint64_t rdtsc()
{
    uint64_t ret;
    asm volatile ( "rdtsc" : "=A"(ret) );
    return ret;
}

static inline void wrmsr(uint32_t msr_id, uint64_t msr_value)
{
    asm volatile ( "wrmsr" : : "c" (msr_id), "A" (msr_value) );
}
