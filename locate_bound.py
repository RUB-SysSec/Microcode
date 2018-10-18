# this script tries to locate the address of the bound instruction
# During processing the script hooks all ROM locations, once the correct triad is found,
# our own microcode will be executed instead of the original bound implementation. Our code
# places a marker in a register, which we can detect and if found, we conclude bound is at the current microcode address.
# As a precaution we blacklist certain address ranges, which we identified as implementing the microcode update process.
# Additionally there is a check whether our microcode update was applied.
# There are false positives, which need to be eliminated manually afterwards.

import sys
import os
sys.path.append("./ucodeapi/")
from ucode import *
from ucodeas import *
from util import *
import struct
from server import *
from ucsp import *
import assembler
import time
import Ucodedecoder
import bitstring as bs

mnem = ("""

;jmp payload
; this location is 0x0011d842

pushad

; load edi with location of the scratch region
mov edi, dword [esp + 0x24]
; copy the "bounds" of 0-0x0fffffff to the start of the scratch region
mov dword [edi], 0x0
mov dword [edi+4], 0x0fffffff

; update CPU with our update
mov eax, 0x104840
mov ecx, 0xc0010020
xor edx, edx
wrmsr

; trigger our microcode
;rdtsc
xor eax, eax
bound eax, [edi]
shrd eax, eax, 1

; restore "noop" microcode update
mov eax, 0x104840
mov dword [eax + 8 * 4], 0xffffffff
mov ecx, 0xc0010020
xor edx, edx
wrmsr

; write register states to buffer
push ebx
mov ebx, dword [esp + 0x28]
mov dword [ebx], eax
pop eax
mov dword [ebx + 0x04], eax
mov dword [ebx + 0x08], ecx
mov dword [ebx + 0x0C], edx
mov dword [ebx + 0x10], esi
mov dword [ebx + 0x14], edi
mov dword [ebx + 0x18], ebp
mov dword [ebx + 0x1C], esp
pushfd
pop eax
mov dword [ebx + 0x20], eax
; restore reg state and return to angry OS
popad
ret
""")

# create server and ucode objects
serial_port = os.environ["MY_SERIALPORT"]
gpio_pins = os.environ["MY_GPIOPINS"]
serv = server(serial_port, gpio_pins)

uc = ucode()
uc.header.loaddefaultheader()

# 0xaca - shrd
# 0x972 - div
uc.header.match_register_list[1] = 0xaca

ucode_rtl = ("""
mov ebp, 0xdead
sll ebp, 16
or ebp, 0xbeef

mov eax, eax
mov eax, eax
mov eax, eax

mov esi, 0x%x

.sw_complete
""")
#uc.set_triads(UcodeAs(ucode_rtl).assemble(), negate=True)

fastpath = False
bytebuf = ""
num_tries = 0
addr = 0x25C
i = 0
first = True

# k10
#rdtsc_hits = [0x52, 0x53, 0x25b, 0x25c, 0x25d, 0x25e, 0x25f, 0x308, 0x309, 0x318, 0x319, 0x31a, 0x31b, 0x31c, 0x334, 0x335, 0x336, 0x337, 0x38b, 0x38c, 0x38d, 0x38e, 0x38f, 0x390, 0x516, 0x517, 0x51f, 0x520, 0x521, 0x522, 0x5dc, 0x5dd, 0x670, 0x671, 0x672, 0x673, 0x6cf, 0x6d0, 0x6d1, 0x895, 0x896, 0x8bd, 0x8be, 0x8bf, 0xd5d, 0xe52, 0xe53, 0xe54, 0xe55, 0xe56, 0xe57, 0xe58]
wrmsr_hits = [0x25b, 0x25c, 0x25d, 0x25e, 0x25f, 0x308, 0x309, 0x334, 0x335, 0x336, 0x337, 0x38b, 0x38c, 0x38d, 0x38e, 0x38f, 0x390, 0x516, 0x517, 0x51f, 0x520, 0x521, 0x522, 0x5dc, 0x5dd, 0x670, 0x671, 0x672, 0x673, 0x6cf, 0x6d0, 0x6d1, 0x895, 0x896, 0xd5d, 0xe52, 0xe53, 0xe54, 0xe55, 0xe56, 0xe57, 0xe58]
#targets = [0x52, 0x53, 0x318, 0x319, 0x31a, 0x31b, 0x31c, 0x8bd, 0x8be, 0x8bf]
# k8
#targets = [0x222, 0x223, 0x224, 0x225, 0x226, 0x25b, 0x25c, 0x25d, 0x25e, 0x25f, 0x308, 0x309, 0x318, 0x319, 0x31a, 0x423, 0x424, 0x425, 0x426, 0x591, 0x592, 0x593, 0x594, 0x595, 0x596, 0x62c, 0x662, 0x663, 0x6a9, 0x6aa, 0x6ab, 0x78b, 0x78c, 0x78d, 0x895, 0x896, 0xadc, 0xadd, 0xade, 0xbf6, 0xbf7, 0xbf8, 0xbf9, 0xbfa, 0xbfb, 0xbfc, 0xbfd, 0xbfe, 0xbff]
targets = range(0x04c0, 0xfe0)

while i < len(targets):
	if not first:
		if not fastpath and num_tries < 1:
			num_tries += 1
		else:
			num_tries = 0
			i += 1
	else:
		first = False
	addr = targets[i]
	# do not test the wrmsr triads
	if addr in wrmsr_hits:
		continue

	if addr % 0x40 == 0:
		print("Currently at address %04X" % addr)

	# set match register to the location we want to test
	uc.header.match_register_list[0] = addr

	# place address in esi
	uc.set_triads(UcodeAs(ucode_rtl % addr).assemble(), negate=True)

	# send ucode update 
	data = uc.getbytes_crypt(True)

	if fastpath:
		serv.wait_for_ready()
	else:
		serv.pwr_on_reset()
		serv.wait_for_connection()
	#print("Connected")
	serv.send_packet(ucsp.get_ucode_packet(data))
	r = serv.get_packet(1, UCSP_TYPE_SET_UCODE_R)
	if r.error != SERVER_ERROR_OK:
		print("Send ucode update failed.")
		print("Address: %04X" % addr)
		fastpath = False
		continue
	#print("Sent ucode update.")

	# send testbench code
	data = assembler.assemble(mnem)
	serv.send_packet(ucsp.get_execute_code_packet(data))
	r = serv.get_packet(1, UCSP_TYPE_EXECUTE_CODE_R)
	if r.error != SERVER_ERROR_OK:
		print("Send testbench failed.")
		print("Address: %04X" % addr)
		fastpath = False
		continue
	#print("Sent testbench.")

	# apply the ucode update
	#serv.send_packet(ucsp.get_apply_ucode_packet())
	serv.send_packet(ucsp.get_execute_code_noupdate_packet())
	ret = serv.get_packet(1, UCSP_TYPE_APPLY_UCODE_R)
	if ret.error != SERVER_ERROR_OK:
		print("Apply ucode update failed.")
		print("Address: %04X" % addr)
		fastpath = False
		continue

	#print('\tapply ucode update succeeded')
	#print('\teax %08x ebx %08x ecx %08x edx %08x' % (ret.value[2], ret.value[3], ret.value[4], ret.value[5]))
	#print('\tesi %08x edi %08x ebp %08x esp %08x' % (ret.value[6], ret.value[7], ret.value[8], ret.value[9]))
	#print('\tefl %08x ticks: %08X' % (ret.value[10], ret.value[1]))

	if ret.value[6] != addr:
		print("Ucode update was not applied. Address: %04X, value: %08X" % (addr, ret.value[6]))
		fastpath = False
		continue


	if ret.value[8] == 0xdeadbeef:
		print("!! Located target at %04X" % addr)
		fastpath = False
		continue

	fastpath = True
