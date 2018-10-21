# build angry_os.bin
# build angry_os.iso
# run angry os in qemu
# load iso to pxe boot server

# credits: wiki.osdev.org, syssec.rub.de */

AS=../i686-elf-4.9.1-Linux-x86_64/bin/i686-elf-as
CC=../i686-elf-4.9.1-Linux-x86_64/bin/i686-elf-gcc

CFLAGS=-c -std=gnu99 -ffreestanding -O2 -Wall -Wextra
LDFLAGS=-T linker.ld -ffreestanding -O2 -nostdlib
LIBS=-lgcc
INCLUDE=-Iinclude -Iinclude/k8_ucode

AS_SOURCES= boot.s cpu_tables.s
AS_OBJECTS=$(AS_SOURCES:.s=.o)

SOURCES=kernel.c libk.c serial.c system.c tty.c ucode.c ucsp.c gdt.c idt.c isr.c mem.c
OBJECTS=$(SOURCES:.c=.o)

OUTPUT=angry_os.iso

all: linker.ld $(AS_SOURCES) $(SOURCES) $(OUTPUT)

$(OUTPUT): angry_os.bin grub.cfg
	cp angry_os.bin isodir/boot/
	cp grub.cfg isodir/boot/grub/
	grub-mkimage -O i386-pc -d /usr/lib/grub/i386-pc/ -o core.img -c load_cfg --prefix=/boot/grub iso9660 biosdisk
	cat /usr/lib/grub/i386-pc/cdboot.img core.img > isodir/boot/grub/i386-pc/eltorito.img
	cat /usr/lib/grub/i386-pc/boot.img core.img > embedded.img
	xorriso -report_about HINT -as mkisofs -graft-points --modification-date=2013061416470300 -b boot/grub/i386-pc/eltorito.img -no-emul-boot -boot-info-table --embedded-boot embedded.img --protective-msdos-label -o angry_os.iso -r isodir --sort-weight 0 / --sort-weight 1 boot
	rm embedded.img
	rm core.img

angry_os.bin: $(AS_OBJECTS) $(OBJECTS)
	$(CC) $(LDFLAGS) -o angry_os.bin $(AS_OBJECTS) $(OBJECTS) $(LIBS)

.s.o:
	$(AS) $< -o $@

.c.o:
	$(CC) $(CFLAGS) $< -o $@ $(INCLUDE)

.PHONY: qemu pxe clean

qemu:
	qemu-system-i386 -cdrom $(OUTPUT)

pxe:
	scp -P 2222 $(OUTPUT) pi@example.com:/usr/tftproot/angry_os.iso

clean:
	rm $(AS_OBJECTS)
	rm $(OBJECTS)
	rm angry_os.bin
	rm $(OUTPUT)