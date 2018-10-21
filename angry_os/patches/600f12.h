/* AMD microcode patch
 *   removed for copyright reasons
 *
 *   this is only required for the non-serial build of angry OS
 *   use the bin2h.py utility to restore the array contents if needed */

/* credits: wiki.osdev.org, syssec.rub.de */

#pragma once

#include <stdint.h>

#define patch_600f12_size 2592

uint8_t patch_600f12[] = {0x00, 0x00};