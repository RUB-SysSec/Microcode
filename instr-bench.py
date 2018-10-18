# Illustrates how to measure the performance of the microcode assisted instruction hook. ESI shows
# the cycles required for the hook.

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
from ucodedis import UcodeDis

def dumpstate(res=[], addr=0, gaincontrol=True, regaincontrol=True, crash=False):
	blocked_regs = ["t33d", "t34d", "t36d", "t37d", "t49d"]
	regs = []
	for i in range(1,23):
		treg = "t%id" % i
		if treg in blocked_regs:
			continue
		regs.append(treg)
	ret = "0x%04X: {\n" % (addr)
	if crash:
		ret += '"crash": True, \n'
	else:
		ret += '"crash": False, \n'
		ret += '"gaincontrol": %r, "regaincontrol": %r,\n' % (gaincontrol, regaincontrol)
		ret += '"eax": 0x%04X, "ebx": 0x%04X, "ecx": 0x%04X, "edx": 0x%04X, "esi": 0x%04X, "edi": 0x%04X, "ebp": 0x%04X, "esp": 0x%04X, "efl": 0x%04X, \n' % (res[2], res[3], res[4], res[5], res[6], res[7], res[8], res[9], res[10])
		i = 11
		for r in regs:
			#print("%s = %08X" % (r, res[i]))
			print(i)
			ret += '"%s": 0x%08X, ' % (r, res[i])
			i += 1
	ret += "\n},"
	return ret

mnem = ("""
jmp payload
; this location is 0x0011d842
; place our signal value in ebp
mov ebp, 0xdeadbeef
; emulate shrd eax, edx, 8
shr eax, 8
push edx
and edx, 0xff
shl edx, 24
or eax, edx
pop edx
; return to normal execution
ret
payload:
; backup all regs
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
mov ebp, 0xffffffff
cpuid
rdtsc
mov edi, eax
shrd ebp, ecx, 4
cpuid
rdtsc
sub eax, edi
mov ebp, eax

push eax
push edx
push ecx

; restore "noop" microcode update
mov eax, 0x104840
mov ecx, 8
noop_loop:
mov dword [eax + ecx * 4], 0xffffffff
inc ecx
cmp ecx, 0xf
jnz noop_loop
mov ecx, 0xc0010020
xor edx, edx
wrmsr

;rdtsc
;mov ebp, edx

pop ecx
pop edx
pop eax

push ebp

cpuid
rdtsc
mov edi, eax
shrd ebp, ecx, 4
cpuid
rdtsc
sub eax, edi
mov esi, eax

pop ebp

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

def getTargetBits(origin, target, bitlen=17):
	val = target - origin + 1
	if val < 0:
		return Bits(int=val, length=bitlen)
	else:
		return Bits(uint=val, length=bitlen)

uc = ucode()
uc.header.loaddefaultheader()
# rdtsc k10
# 0x318 -> 0x319 -> 0x31a -> 0x8bd -> 0x8be -> 0x8bf -> 0x52 -> 0x53 -> 0x31b -> 0x31c?
# if the last triad is hooked, the cpu crashes with a page fault or otherwise goes into a failure state
# rdtscp k10
# 0x9da -> 0x319 -> 0x31a -> 0x8bd -> 0x8be -> 0x8bf -> 0x52 -> 0x53 -> 0x31b -> 0x31c?
# if the last triad is hooked, the cpu crashes with a GPF
# rdtsc k8
# 0x318 -> 0x319 -> 0x31a?
# if the last triad is hooked, the cpu crashes with a GPF
# bound k10
# 0x120 -> 0x121 -> 

# k10 rdtsc
targets = [0x52, 0x53, 0x318, 0x319, 0x31a, 0x31b, 0x31c, 0x8bd, 0x8be, 0x8bf]
# k10 rdmsr 0x10 (rdtsc)
targets = [0x52, 0x53, 0x328, 0x329, 0x841, 0x842, 0x843, 0x8bd, 0x8be, 0x8bf, 0xd51, 0xe68, 0xe69, 0xe6a]
# k10 rdtscp
#targets = [0x52, 0x53, 0x319, 0x31a, 0x31b, 0x31c, 0x8bd, 0x8be, 0x8bf, 0x9da]
#k8 rdtsc
#targets = [0x318, 0x319, 0x31a]
# bound
#targets = [0x120, 0x121, 0x965]

# 0xaca - shrd
# 0x972 - div

uc.header.match_register_list[0] = 0xaca
ucode_rtl = (
"""
.start 0x0

mov t1d, 0xdead
sll t1d, 16
or t1d, 0xbeef

sub.Z t1d, regmd4
jcc EZF, 2
add eax, 0

dbg 0   000010001 0       1      101111 001 0        0     0   000     0011   110  010000 1       100000 00     001100 000000000
dbg 0   000010101 0       1      101100 100 0        0     0   000     1111   010  010001 1       100000 00     110000 000000000
dbg 0   000010101 0       1      101000 000 0        1     0   000     1111   010  010010 1       100000 00     110000 000000000

.sw_complete

dbg 0   000111010 0       1      010000 001 0        0     0   000     0011   110  010000 1       000000 00     000100 010000000
dbg 0   000000001 0       1      010010 100 0        0     0   000     1111   010  101000 1       000000 00     010000 000000000
dbg 0   101010010 1       1      101000 000 1        0     1   000     1111   010  111111 1       101000 00     110000 000000000

// push nextdecode pc
mov edx, pcd
sub esp, 0x4
st [esp], edx

// load location of x86 code
mov t1d, 0x0011
sll t1d, 16
or t1d, 0xd842

// redirect x86 control flow
add eax, 0
add eax, 0
writepc t1d

.sw_complete
""")

uc.set_triads(UcodeAs(ucode_rtl).assemble(), negate=True)

ud = UcodeDis(uc)

#print(ud.analyzeTriad(0))
#exit(0)

fastpath = True
bytebuf = ""

#with open("newupdate.bin", "wb") as f:
#	f.write(uc.getbytes_crypt(True))

for addr in range(0, 1):

	# send ucode update
	data = uc.getbytes_crypt(True)

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
		fastpath = False
		continue
	print("Sent ucode update.")

	# send testbench code
	data = assembler.assemble(mnem)
	#print(len(data))
	serv.send_packet(ucsp.get_execute_code_packet(data))
	r = serv.get_packet(1, UCSP_TYPE_EXECUTE_CODE_R)
	if r.error != SERVER_ERROR_OK:
		print("Send testbench failed.")
		fastpath = False
		continue
	print("Sent testbench.")

	# apply the ucode update
	#serv.send_packet(ucsp.get_apply_ucode_packet())
	serv.send_packet(ucsp.get_execute_code_noupdate_packet())
	ret = serv.get_packet(1, UCSP_TYPE_APPLY_UCODE_R)
	if ret.error != SERVER_ERROR_OK:
		print("Apply ucode update failed.")
		fastpath = False
		continue

	print('\tapply ucode update succeeded')
	print('\teax %08x ebx %08x ecx %08x edx %08x' % (ret.value[2], ret.value[3], ret.value[4], ret.value[5]))
	print('\tesi %08x edi %08x ebp %08x esp %08x' % (ret.value[6], ret.value[7], ret.value[8], ret.value[9]))
	print('\tefl %08x ticks: %08X' % (ret.value[10], ret.value[1]))
	#print('\tcustom: %08x' % (ret.value[63]))
	#print(dumpstate(ret.value, addr))
	#print("Diff: %i" % ((ret.value[8] - ret.value[7])))
	fastpath = True
