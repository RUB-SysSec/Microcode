from bitstring import Bits
import math
from defs import *

class UcodeAs(object):
	def __init__(self, asm):
		self.asm = asm

	def __asm_is_op(self, opcode):
		return opcode.split('.', 1)[0] in reg_ops or opcode.split('.', 1)[0] in ldst_ops or opcode.split('.', 1)[0] in br_ops or opcode.split('.', 1)[0] == "dbg"

	def __asm_get_op(self, opcode, operands):
		if opcode.split('.', 1)[0] == "dbg":
			opstr = "".join(operands)
			return RegOp(opcode+" ,", debug=opstr)
		if opcode.split('.', 1)[0] in reg_ops:
			return RegOp(opcode + ' ' + operands)
		elif opcode.split('.', 1)[0] in ldst_ops:
			return LdStOp(opcode + ' ' + operands)
		elif opcode.split('.', 1)[0] in br_ops:
			return BrOp(opcode + ' ' + operands)
		return None

	def assemble(self):
		uop_pos = 0
		uops = [None, None, None]
		sw = SW('next')
		stream = Bits(length=0)

		for line in self.asm.split('\n'):
			line = line.strip()

			if len(line) == 0:
				continue

			if line.startswith('//'):
				continue

			if line.startswith('.start'):
				continue

			if line.startswith('.sw_complete'):
				sw = SW('complete')
				continue

			if line.startswith('.test'):
				sw = SW('test')
				continue

			if line.startswith('.sw_branch'):
				sw = SW('branch', addr=int(line[11:], 0))
				continue

			if line.startswith('.sw_dbg'):
				sw = SW('dbg', dbg=line[8:])
				continue

			opcode = line.split(' ', 1)[0].lower()
			operands = line.split(' ', 1)[1].lower()

			if not self.__asm_is_op(opcode):
				raise ValueError('Invalid opcode: %s' % opcode)
				continue

			if opcode in op_constraints.keys():
				constraint = op_constraints[opcode]

				if constraint < uop_pos:
					for i in range(3):
						if uops[i] == None:
							uops[i] = NoOp()
					stream += Triad(uops[0], uops[1], uops[2], sw).bits()
					uop_pos = 0
					uops = [None, None, None]
					sw = SW('next')

				if constraint > uop_pos:
					while(constraint > uop_pos):
						uops[uop_pos] = NoOp()
						uop_pos += 1

			if uop_pos < 3:
				uops[uop_pos] = self.__asm_get_op(opcode, operands)
				uop_pos += 1
			else:
				stream += Triad(uops[0], uops[1], uops[2], sw).bits()
				uop_pos = 1
				uops = [self.__asm_get_op(opcode, operands), None, None]
				sw = SW('next')

		if uop_pos > 0 and uop_pos <= 3:
			for i in range(3):
				if uops[i] == None:
					uops[i] = NoOp()
			stream += Triad(uops[0], uops[1], uops[2], sw).bits()

		return stream

class Triad(object):
	def __init__(self, op1, op2, op3, sw):
		self.op1 = op1
		self.op2 = op2
		self.op3 = op3
		self.sw = sw

	def bits(self):
		return self.op1.bits() + self.op2.bits() + self.op3.bits() + self.sw.bits() 

	def bytes(self):
		return self.bits().tobytes()

class BaseOp(object):
	def __init__(self, mnem):
		mnem = mnem.lower()
		self.operation = mnem.split(' ', 1)[0]
		ops_mnem = mnem.split(' ', 1)[1].replace(' ', '').split(',')
		self.operands = tuple(Operand(op) for op in ops_mnem)
		self.swapOpsBit = Bits(bin='0')
		self.commitPZSBit = Bits(bin='0')
		self.commitCBit = Bits(bin='0')
		self.sizeMSB = Bits(bin='0')
		self.Uk4 = Bits(bin='000000')
		if "." in self.operation:
			flags = self.operation.split('.', 1)[1]
			self.operation = self.operation.split('.', 1)[0]
			if "e" in flags:
				self.swapOpsBit = Bits(bin='1')
			if "p" in flags or "z" in flags or "s" in flags:
				self.commitPZSBit = Bits(bin='1')
			if "c" in flags:
				self.commitCBit = Bits(bin='1')
			if "q" in flags:
				self.sizeMSB = Bits(bin='1')

	def bytes(self):
		return self.bits().tobytes()

class BrOp(BaseOp):
	def __init__(self, mnem):
		super(BrOp, self).__init__(mnem)

	def bits(self):

		if len(self.operands) != 2:
			print('BrOp got %i arguments, 2 expected!' % len(self.operands))

		if self.operation != 'jcc':
			print('BrOp got unknown operation (%s), jcc expected!' % self.operation)

		if self.operands[1].type != OP_TYPE_IMM:
			print('BrOp needs immediate as second operand type!')

		cc = next((cc for cc in k10_cc if cc['mnem'].lower() == self.operands[0].mnem), None)
		if cc == None:
			print('BrOp first operand needs to be one of k10_cc!')

		r = Bits(1) # unkn
		r+= Bits(bin='0101') # cond ucode branch
		r+= self.operands[0].bits() # cc
		r+= Bits(bin='11') # xchg src/dst, 3 op mode
		r+= Bits(bin='111001') # always zero register, TODO: verify and add to k10_regs
		r+= Bits(bin='101') # branch target rom/ram indicator

		r+= self.commitPZSBit # commit p, z and s flag
		r+= self.commitCBit # commit c flag
		r+= Bits(1) # unkn

		r+= Bits(bin='000') # RegOp/SpecOp
		r+= Bits(bin='1111') # segment
		r+= Bits(bin='011') # size

		r+= Bits(bin='111011') # always zero register, TODO: verify and add to k10_regs

		r+= Bits(bin='0') # immediate mode
		r+= Bits(bin='000000') # unkn

		r+= self.operands[1].bits(bitlen=17)

		if len(r) != 64:
			print('BrOp has size of %i bit, 64 bit expected!' % len(r))

		return r


class LdStOp(BaseOp):
	def __init__(self, mnem):
		super(LdStOp, self).__init__(mnem)

	def operation_bits(self):
		op = next((op for op in k10_operations if op['mnem'] == self.operation), None)
		return Bits(bin=op['bits'])

	def bits(self):

		if len(self.operands) != 2:
			print('LdStOp got %i arguments, 2 expected!' % len(self.operands))

		is_load_op = False
		if self.operation == 'ld':
			is_load_op = True
		elif self.operation == 'st':
			is_load_op = False
		else:
			print('LdStOp got unknown operation (%s), ld or st expected!' % self.operation)

		if is_load_op:
			if self.operands[0].type != OP_TYPE_REG:
				print('Load needs register as first operand type!')
			if self.operands[1].type != OP_TYPE_MEM:
				print('Load needs memory as second operand type!')
		else:
			if self.operands[0].type != OP_TYPE_MEM:
				print('Store needs memory as first operand type!')
			if self.operands[1].type != OP_TYPE_REG:
				print('Store needs register as second operand type!')

		r = Bits(1) # unkn
		r+= self.operation_bits() # operation

		if is_load_op:
			r+= Bits(bin='1') # swap src and dst
		else:
			r+= Bits(bin='0') # swap src and dst

		r+= Bits(1) # 2/3 operand mode

		if is_load_op:
			r+= self.operands[1].bits() # memory type src
			r+= Bits(bin='000') # unknown
		else:
			r+= self.operands[0].bits() # memory type dst
			r+= Bits(bin='100') # unknown

		r+= self.commitPZSBit # commit p, z and s flag
		r+= self.commitCBit # commit c flag
		r+= Bits(1) # unkn

		if is_load_op:
			r+= Bits(bin='001') # LdStOp (load)
		else:
			r+= Bits(bin='010') # LdStOp (store)

		if is_load_op:
			r+= self.operands[1].seg_bits() # memory type src segment reg
		else:
			r+= self.operands[0].seg_bits() # memory type dst segment reg

		r+= self.sizeMSB
		r+= Bits(uint=int(math.log(self.operands[1].size, 2) - 3), length=2) # size
		r+= Bits(bin='111111') # always zero register, TODO: verify and add to k10_regs

		r+= Bits(bin='1') # register mode
		r+= Bits(7) # unkn
		r+= Bits(1) # unkn

		if is_load_op:
			r+= self.operands[0].bits() # register type dst
		else:
			r+= self.operands[1].bits() # register type src

		r+= Bits(9) # unkn

		if len(r) != 64:
			print('LdStOp has size of %i bit, 64 bit expected!' % len(r))

		return r

class RegOp(BaseOp):
	def __init__(self, mnem, debug_op=None, debug=None):
		super(RegOp, self).__init__(mnem)
		self.debug_op = debug_op
		self.debug = debug
		self.unk2 = Bits(bin='100')
		self.opCountOverwrite = None
		# this unknown op has different bits at this position
		# for now overwrite them so the div hook works
		if self.operation == 'div2':
			self.unk2 = Bits(bin='010')
		# lea uses special encoding, swapops is on, t35 is an implicit third register, target and source are swapped and Uk4 is set
		elif self.operation == 'lea':
			if len(self.operands) != 2:
				raise ValueError("lea expects exactly 2 arguments: lea destination, baseregister")
			tops = [None, None, None]
			# lea has 3 operands, but does not set the 3 operand flag
			self.opCountOverwrite = Bits(bin='0')
			# set the swap ops bit
			self.swapOpsBit = Bits(bin='1')
			# set the Uk4 field
			self.Uk4 = Bits(bin='010000')
			# dst, hardcoded t35
			tops[0] = Operand("t35d")
			# src1, base register
			tops[1] = self.operands[1]
			# src2, target register
			tops[2] = self.operands[0]
			self.operands = tops


	def operation_bits(self):
		if not self.debug_op:
			op = next((op for op in k10_operations if op['mnem'] == self.operation), None)
			return Bits(bin=op['bits'])
		else:
			return Bits(uint=self.debug_op, length=9)

	def bits(self):

		if self.debug:
			bs = self.debug.replace(' ', '')
			return Bits(bin=bs)

		# fix for decoding SpecOp jmp/writePC as RegOp
		if self.operation == 'jmp' or self.operation == 'writepc':
			self.operands = (self.operands[0], self.operands[0])

		if len(self.operands) < 2 or len(self.operands) > 3 :
			print('RegOp got %i arguments, 2 or 3 expected!' % len(self.operands))

		if self.operands[0].type != OP_TYPE_REG:
			print('RegOp first operand must be reg!')

		r = Bits(1) # unkn
		r+= self.operation_bits() # operation
		r+= self.swapOpsBit # swap src and dst

		if len(self.operands) == 2:
			# special handling for (at first) lea, overwrite the opcount flag
			if self.opCountOverwrite != None:
				r+= self.opCountOverwrite
			else:
				r+= Bits(bin='0') # 1 src
			r+= self.operands[0].bits() # dst
			r+= self.unk2 # unkn
			r+= self.commitPZSBit # commit p, z and s flag
			r+= self.commitCBit # commit c flag
			r+= Bits(1) # unkn
			r+= Bits(3) # RegOp
			r+= Bits(bin='0000') # seg
			r+= self.sizeMSB
			r+= Bits(uint=int(math.log(self.operands[0].size, 2) - 3), length=2) # size
			r+= Bits(6) # dst for 2 src
			last_operand = self.operands[1] # src
		elif len(self.operands) == 3:
			# special handling for (at first) lea, overwrite the opcount flag
			if self.opCountOverwrite != None:
				r+= self.opCountOverwrite
			else:
				r+= Bits(bin='1') # 2 src
			r+= self.operands[1].bits() # src1
			r+= self.unk2 # unkn
			r+= self.commitPZSBit # commit p, z and s flag
			r+= self.commitCBit # commit c flag
			r+= Bits(1) # unkn
			r+= Bits(3) # RegOp
			r+= Bits(bin='0000') # seg
			r+= self.sizeMSB
			r+= Bits(uint=int(math.log(self.operands[0].size, 2) - 3), length=2) # size
			r+= self.operands[0].bits() # dst
			last_operand = self.operands[2] # src2

		if last_operand.type == OP_TYPE_REG:
			r+= Bits(bin='1') # reg instead of imm
			#r+= Bits(7) # unkn
			r+= self.Uk4
			r+= Bits(1)
			r+= Bits(1) # unkn
			r+= last_operand.bits() # src reg
			r+= Bits(9) # unkn
		elif last_operand.type == OP_TYPE_IMM:
			r+= Bits(bin='0') # imm type
			#r+= Bits(7) # unkn
			r+= self.Uk4
			r+= Bits(1)
			r+= last_operand.bits(16)

		if len(r) != 64:
			print('RegOp has size of %i bit, 64 bit expected!' % len(r))

		return r

class Operand(object):
	def __init__(self, mnem):
		self.mnem = mnem

		cc = next((cc for cc in k10_cc if cc['mnem'].lower() == self.mnem), None)
		if cc != None:
			self.type = OP_TYPE_CC
			self.size = 5
			self.cc = cc

		elif '[' in mnem and mnem[-1:] == ']':
			seg_reg = ''# next((s for s in k10_segregs if s['mnem'] == 'es'), None)
			mem_reg = ''
			if not ':' in mnem:
				mem_reg = mnem[1:-1]
				seg_reg = 'ds'
			else:
				mem_reg = mnem.split(':', 1)[1][1:-1]
				seg_reg = mnem.split(':', 1)[0]
			self.reg = next((r for r in k10_regs if mem_reg in r['mnem']), None)
			self.seg = next((s for s in k10_segregs if s['mnem'] == seg_reg), None)
			if self.reg != None and self.seg != None:
				self.type = OP_TYPE_MEM
				self.size = 32

		else:
			self.reg = next((r for r in k10_regs if mnem in r['mnem']), None)
			if self.reg == None:
				self.type = OP_TYPE_IMM
				self.size = len(mnem)
			else:
				self.type = OP_TYPE_REG
				self.size = 2**(self.reg['mnem'].index(mnem) + 3)

		if self.type == None:
			print('Unknown operand (%s)!' % self.mnem)

	def bits(self, bitlen=32):
		if self.type == OP_TYPE_REG or self.type == OP_TYPE_MEM:
			return Bits(bin=self.reg['bits'])
		elif self.type == OP_TYPE_IMM:
			val = int(self.mnem, 0)
			if val < 0:
				return Bits(int=val, length=bitlen)
			else:
				return Bits(uint=val, length=bitlen)
		elif self.type == OP_TYPE_CC:
			return Bits(bin=self.cc['bits'])

	def seg_bits(self):
		if self.type == OP_TYPE_MEM:
			return Bits(bin=self.seg['bits'])
		else:
			raise ValueError('No segment register for non memory operand type!')

class SW(object):
	def __init__(self, act, addr=0, dbg=None):
		self.act = act
		self.addr = addr
		self.dbg = dbg

	def bits(self):
		if self.dbg != None:
			self.dbg.replace(" ", "")
			r = Bits(bin=self.dbg)
			if len(r) != 32:
				raise ValueError('SW has size of %i bit, 32 bit expected!' % len(r))
			return ~r
		actionBits = getSwActionBitsByMnem(self.act)
		if actionBits == None:
			raise ValueError('Invalid sequence word!')

		if self.act == 'branch':
			r = Bits(bin='111111111111110') # unkn
			r+= actionBits # action
			r+= Bits(bin='10') # unkn
			r+= Bits(uint=self.addr, length=12) # addr

		elif self.act == 'complete':
			r = Bits(bin='111111111111111')
			r+= actionBits # action
			r+= Bits(bin='11')
			r+= Bits(bin='111111111111')

		# old encoding for next triad sequence word
		#elif self.act == 'next':
		#	r = Bits(bin='111111111111111')
		#	r+= actionBits # action
		#	r+= Bits(bin='11')
		#	r+= Bits(bin='111111111111')

		elif self.act == 'next':
			r = Bits(bin='111111111111110')
			r+= Bits(bin='000')
			r+= Bits(bin='10')
			r+= Bits(bin='000000000000')

		if len(r) != 32:
			raise ValueError('SW has size of %i bit, 32 bit expected!' % len(r))

		r = ~r # invert
		return r

def NoOp():
	return RegOp('add eax, 0')