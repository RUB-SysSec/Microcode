# Illustrates the ISR. The TEA calculation is first performed using standard x86 assembly and then again using
# the hooked shrd instruction for all supported operations. The randomized code is also generated in this script.

import sys
import os
sys.path.append("../ucodeapi/")
from ucode import *
from ucodeas import *
from util import *
import struct
from server import *
from ucsp import *
import assembler
import time
import Ucodedecoder
from ucodedis import UcodeDis

dataBase = 0x0011d844

teaData = ("""
msg0: dd 0xc0feb4b3
msg1: dd 0xdeadbeef
key0: dd 0x42424242
key1: dd 0x42424242
key2: dd 0x42424242
key3: dd 0x42424242
rc:   dd 0x9E3779B9
end:  dd 0x6526B0D9
""")

teaAsm = ("""
mov esi, [msg0]
mov edi, [msg1]
mov ecx, [rc]

tea_loop:

; ((edi << 4) + key[0])
mov ebx, edi
shl ebx, 4
mov edx, [key0]
add ebx, edx

; ^ (edi + ecx)
mov eax, edi
add eax, ecx
xor ebx, eax

; ^ ((edi >> 5) + key[1])
mov eax, edi
shr eax, 5
mov edx, [key1]
add eax, edx
xor ebx, eax

; esi +=
add esi, ebx

; ((esi << 4) + key[2])
mov ebx, esi
shl ebx, 4
mov edx, [key2]
add ebx, edx

; ^ (esi + ecx)
mov eax, esi
add eax, ecx
xor ebx, eax

; ^ ((esi >> 5) + key[3])
mov eax, esi
shr eax, 5
mov edx, [key3]
add eax, edx
xor ebx, eax

; edi +=
add edi, ebx

; ecx += rc
mov edx, [rc]
add ecx, edx

; if ecx != end goto tea_loop
mov edx, [end]
cmp ecx, edx
jne tea_loop

""")

teaAsm1 = ("""
mov esi, [msg0]
mov edi, [msg1]
mov ecx, [rc]

add edi, ecx
add esi, edi
mov edi, esi
add esi, esi
shr esi, 8
add esi, edi
""")

regs = ('eax', 'ecx', 'ebx', 'edx', 'esi', 'edi', 'ebp', 'esp')
ops = ('shl', 'shr', 'add', 'xor')

def convertToRandomIsa(inputDefs, inputAsm):
	defs = []
	for line in inputDefs.split('\n'):

		if not line or ':' not in line:
			continue

		defs.append(line.split(':')[0].strip())

	output = []
	for line in inputAsm.split('\n'):

		commentIndex = line.find(';')
		if commentIndex != -1:
			line = line[:commentIndex]

		line = line.strip()

		if not line:
			continue

		parts = line.split(' ')
		if len(parts) == 3:

			insn, op1, op2 = parts
			op1 = op1[:-1]

			if insn == 'mov' and op1 in regs:

				if op2 in regs:
					line = 'bound ' + op1 + ', [' + op2 + ' + 0x%x]' % 0x0

				elif op2[1:-1] in defs:
					line = 'bound ' + op1 + ', [eax + 0x%x]' % ((defs.index(op2[1:-1]) << (16+2)) + 0x1)

			elif insn in ops and op1 in regs:

				if op2 in regs:
					line = 'bound ' + op1 + ', [' + op2 + ' + 0x%x]' % (ops.index(insn) + 2)

				else:
					line = 'bound ' + op1 + ', [eax + 0x%x]' % ((int(op2) << 16) + ops.index(insn) + 2)

		elif line.endswith(':'):
			line = line[:-1] + '_isr:'

		elif line.startswith('j') and not line.endswith(':'):
			line = parts[0] + ' ' + parts[1] + '_isr'

		output.append(line)

	return '\n'.join(output)

teaRandomAsm = convertToRandomIsa(teaData, teaAsm)

myasm = convertToRandomIsa(teaData, teaAsm1)
print(myasm)
exit(0)

mnem = ("""
; set base address
org 0x0011d840

; jump over data
jmp start

; align to 32 bit addresses for data
algn: dw 0x0000

; insert user data
"""
+
teaData
+
"""

; code start
start:

; save regs
pushad

; insert user code, measure clock cycles
rdtsc
push eax
"""
+
teaAsm
+
"""
rdtsc
pop ebx
sub eax, ebx

; push results
push eax
push esi
push edi

; apply microcode update
mov eax, 0x104840
mov ecx, 0xc0010020
xor edx, edx
wrmsr

rdtsc
push eax
"""
+
teaRandomAsm
+
"""
rdtsc
pop ebx
sub eax, ebx

; push results
push eax
push esi
push edi
push ebp

mov eax, 0x104840
mov dword [eax + 8 * 4], 0xffffffff
mov ecx, 0xc0010020
xor edx, edx
wrmsr

pop edx
pop edi
pop esi
pop ebp

pop ebx
pop eax
pop ecx

; log register contents, restore old values, return
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
popad
ret
""")

ucode_rtl = ("""
.start 0x0

// load 
lea t1d, t56d
xor.ez t1w, t1w, 0x0000
jcc EZF, 0xa

xor.ez t1w, t1w, 0x0001
jcc EZF, 0x6
xor.ez t1w, t1w, 0x0002

jcc EZF, 0x4
xor.ez t1w, t1w, 0x0003
jcc EZF, 0x3

xor.ez t1w, t1w, 0x0004
jcc EZF, 0x1
xor regmd6, regmd4

mov ebp, 0xbeef
jcc True, 0xa
add t1d, 0

add regmd6, regmd4
jcc True, 0x9
add t1d, 0

srl t2d, t1d, 0x10
srl regmd6, t2d
jcc True, 0x8

srl t2d, t1d, 0x10
sll regmd6, t2d
jcc True, 0x7

mov t2d, 0x0011
sll t2d, 0x10
add t2d, 0xd844

srl t3d, t1d, 0x10
add t2d, t3d
ld regmd6, [t2d]

jcc True, 0x4
add t1d, 0
add t1d, 0

mov regmd6, regmd4
add t1d, 0
add t1d, 0

add t1d, 0
add t1d, 0
add t1d, 0

add t1d, 0
add t1d, 0
add t1d, 0

add t1d, 0
add t1d, 0
add t1d, 0

add t1d, 0
add t1d, 0
add t1d, 0
// faster sw_complete
.sw_dbg 111111111111110 001      00  000000000000

add t1d, 0
add t1d, 0
add t1d, 0

""")


# create server and ucode objects
serial_port = os.environ["MY_SERIALPORT"]
gpio_pins = os.environ["MY_GPIOPINS"]
serv = server(serial_port, gpio_pins)

uc = ucode()
uc.header.loaddefaultheader()
uc.header.match_register_list[0] = 0x120
#uc.header.init_flag = 1
uc.set_triads(UcodeAs(ucode_rtl).assemble(), negate=True)

# send ucode update
data = uc.getbytes_crypt(True)

# append HMAC
data+= struct.pack('<LL', 0x8abf7f10, 0x5c17c730)

fastpath = True
if fastpath:
	serv.wait_for_ready()
else:
	serv.pwr_on_reset()
	serv.wait_for_connection()
print("Connected")
serv.send_packet(ucsp.get_ucode_packet(data))
r = serv.get_packet(1, UCSP_TYPE_SET_UCODE_R)
if r.error != SERVER_ERROR_OK:
	print("Send ucode update failed.")
	quit(0)
print("Sent ucode update.")

# send testbench code
data = assembler.assemble(mnem)
serv.send_packet(ucsp.get_execute_code_packet(data))
r = serv.get_packet(1, UCSP_TYPE_EXECUTE_CODE_R)
if r.error != SERVER_ERROR_OK:
	print("Send testbench failed.")
	quit(0)
print("Sent testbench.")

# apply the ucode update
#serv.send_packet(ucsp.get_apply_ucode_packet())
serv.send_packet(ucsp.get_execute_code_noupdate_packet())
ret = serv.get_packet(1, UCSP_TYPE_APPLY_UCODE_R)
if ret.error != SERVER_ERROR_OK:
	print("Apply ucode update failed.")
	quit(0)

print('\tapply ucode update succeeded')
print('\teax %08x ebx %08x ecx %08x edx %08x' % (ret.value[2], ret.value[3], ret.value[4], ret.value[5]))
print('\tesi %08x edi %08x ebp %08x esp %08x' % (ret.value[6], ret.value[7], ret.value[8], ret.value[9]))
print('\tefl %08x ticks: %i/%i' % (ret.value[10], ret.value[0], ret.value[1]))
