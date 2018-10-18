from bitstring import Bits
import math
from defs import *

def bitstr(bits):
	s = []
	for bit in bits:
		if bit:
			s.append('1')
		else:
			s.append('0')
	return ''.join(s)

EQ = lambda a, b: a == b
NEQ = lambda a, b: a != b

class Condition(object):
	def __init__(self, fieldName, compareFn, value):
		self.fieldName = fieldName
		self.compareFn = compareFn
		self.value = value

	def evaluate(self, bits):
		field = opFields.getDefByName(self.fieldName)
		fieldBits = next(bits.cut(field['length'], field['position'], count=1))
		if self.compareFn(fieldBits, self.value):
			return True
		return False

class OpFields(object):
	def __init__(self):
		self.opFields = []

	def addDef(self, length, position, name, letter, condition=None):
		self.opFields.append({'length':length, 'position':position, 'name':name, 'letter':letter, 'condition':condition})

	def getDefsByPosition(self, position):
		return (d for d in self.opFields if d['position'] == position)

	def getDefByName(self, name):
		return next((d for d in self.opFields if d['name'] == name))

	def getDefs(self):
		return self.opFields

opFields = OpFields()
opFields.addDef( 1,  0, 'Uk1'      , 'u')
opFields.addDef( 9,  1, 'Operation', 'o', [Condition('ShortOprn', NEQ, getOprnBitsByMnem('jcc'))])
opFields.addDef( 4,  1, 'ShortOprn', 'o', [Condition('ShortOprn',  EQ, getOprnBitsByMnem('jcc'))])
opFields.addDef( 5,  5, 'Condition', 'c')
opFields.addDef( 1, 10, 'SwapOps'  , 'x')
opFields.addDef( 1, 11, 'OpMode'   , 'm')
opFields.addDef( 6, 12, 'Op1'      , '1')
opFields.addDef( 3, 18, 'Uk2'      , 'u')
opFields.addDef( 1, 21, 'PZSFlags' , 'f')
opFields.addDef( 1, 22, 'CFlag'    , 'f')
opFields.addDef( 1, 23, 'Uk3'      , 'u')
opFields.addDef( 3, 24, 'OpClass'  , 'C')
opFields.addDef( 4, 27, 'SegReg'   , 's')
opFields.addDef( 3, 31, 'Size'     , 'z')
opFields.addDef( 6, 34, 'Op2'      , '2')
opFields.addDef( 1, 40, 'RegMode'  , 'r')
opFields.addDef( 6, 41, 'Uk4'      , 'u')
opFields.addDef( 2, 47, 'Uk5Reg'   , 'u', [Condition('RegMode',    EQ, Bits(bin='1'))])

opFields.addDef( 1, 47, 'Uk5Imm'   , 'u', [Condition('RegMode',   NEQ, Bits(bin='1')),
                                           Condition('ShortOprn', NEQ, getOprnBitsByMnem('jcc'))])

opFields.addDef(17, 47, 'RomAddr'  , 'a', [Condition('RegMode',   NEQ, Bits(bin='1')),
                                           Condition('ShortOprn',  EQ, getOprnBitsByMnem('jcc'))])

opFields.addDef(16, 48, 'Imm'      , 'i', [Condition('RegMode',   NEQ, Bits(bin='1')),
                                           Condition('ShortOprn', NEQ, getOprnBitsByMnem('jcc'))])

opFields.addDef( 6, 49, 'Op3'      , '3', [Condition('RegMode',    EQ, Bits(bin='1'))])

opFields.addDef( 9, 55, 'Uk6Reg'   , 'u', [Condition('RegMode',    EQ, Bits(bin='1'))])


class Operation(object):
	def __init__(self, bits=None):
		self.bits = bits

	def getFieldMnem(self, field):
		if field['name'] == 'Operation':
			return getOprnMnemByBits(field['bits'])

		elif field['name'] == 'ShortOprn' and field['bits'] == getOprnBitsByMnem('jcc'):
			return 'jcc'

		elif field['name'] == 'Op1' or field['name'] == 'Op2' or field['name'] == 'Op3':
			sizeDef = opFields.getDefByName('Size')
			sizeBits = next(self.bits.cut(sizeDef['length'], sizeDef['position'], count=1))
			return getRegMnemByBits(field['bits'], sizeBits)

		elif field['name'] == 'Condition':
			return getCondMnemByBits(field['bits'])

		elif field['name'] == 'SegReg':
			return getSegMnemByBits(field['bits'])

		elif field['name'] == 'OpClass':
			return getClassMnemByBits(field['bits'])

		elif field['name'] == 'Size':
			return ('%ub' % (2**((field['bits'].uint & 3) + 3)))

		elif field['name'] == 'Imm' or field['name'] == 'RomAddr':
			return ('0x%x' % field['bits'].int)

		return ''

	def getNextField(self, pos):
		defs = list(opFields.getDefsByPosition(pos))
		if len(defs) == 0:
			return None

		if len(defs) == 1:
			field = defs[0].copy()
			field['bits'] = next(self.bits.cut(field['length'], field['position'], count=1))
			field['mnem'] = self.getFieldMnem(field)
			return field
		
		selectedDef = None
		for definition in defs:
			if definition['condition'] == None:
				continue

			allTrue = False
			for cond in definition['condition']:
				if not cond.evaluate(self.bits):
					allTrue = False
					break

				allTrue = True

			if allTrue:
				selectedDef = definition
				break

		if selectedDef == None:
			raise ValueError('No definition matches condition, error in OpField definitions!')
			return None

		field = selectedDef.copy()
		field['bits'] = next(self.bits.cut(field['length'], field['position'], count=1))
		field['mnem'] = self.getFieldMnem(field)
		return field

	def getMnem(self):
		operation = None
		swapOps = None
		opMode = None
		op1 = None
		op2 = None
		op3 = None
		imm = None

		pos = 0
		while(True):
			field = self.getNextField(pos)
			if field == None:
				break

			if field['name'] == 'Operation' or field['name'] == 'ShortOprn':
				operation = field['mnem']
			elif field['name'] == 'SwapOps':
				swapOps = field['bits'].uint == 1
			elif field['name'] == 'OpMode':
				opMode = field['bits'].uint == 1
			elif field['name'] == 'Op1':
				op1 = field['mnem']
			elif field['name'] == 'Op2':
				op2 = field['mnem']
			elif field['name'] == 'Op3':
				op3 = field['mnem']
			elif field['name'] == 'Imm' or field['name'] == 'RomAddr':
				imm = field['mnem']

			pos += field['length']

		if op3 == None:
			op3 = imm

		if opMode == False:
			if swapOps == False:
				return (operation, op2, op1)
			else:
				return (operation, op1, op2)
		else:
			if swapOps == False:
				return (operation, op2, op1, op3)
			else:
				return (operation, None, op1, op2, op3)

	def genAnalysisOutput(self):
		nameLine = ''
		letterLine = ''
		bitsLine = ''
		mnemLine = ''

		pos = 0
		while(True):
			field = self.getNextField(pos)
			if field == None:
				break

			fieldLen = max(len(field['name']), len(field['bits']), len(field['mnem']))
			fieldLen += 1

			formatString = '%%-%is' % fieldLen
			nameLine += formatString % field['name']
			letterLine += formatString % (len(field['bits']) * field['letter'])
			bitsLine += formatString % bitstr(field['bits'])
			mnemLine += formatString % field['mnem']

			pos += field['length']

		return nameLine + '\n' + letterLine + '\n' + bitsLine + '\n' + mnemLine

swFields = OpFields()
swFields.addDef(15,  0, 'Uk1'    , 'u')
swFields.addDef( 3, 15, 'Action' , 'o')
swFields.addDef( 2, 18, 'Uk2'    , 'u')
swFields.addDef(12, 20, 'RomAddr', 'a')

class SequenceWord(object):
	def __init__(self, bits):
		self.bits = ~bits # negate

	def getFieldMnem(self, field):
		if field['name'] == 'Action':
			return getSwActionMnemByBits(field['bits'])
		elif field['name'] == 'RomAddr':
			return ('0x%x' % field['bits'].uint)

		return ''

	def getNextField(self, pos):
		defs = list(swFields.getDefsByPosition(pos))
		if len(defs) != 1:
			return None

		field = defs[0].copy()
		field['bits'] = next(self.bits.cut(field['length'], field['position'], count=1))
		field['mnem'] = self.getFieldMnem(field)
		return field

	def getMnem(self):
		action = None
		romAddr = None

		pos = 0
		while(True):
			field = self.getNextField(pos)
			if field == None:
				break

			if field['name'] == 'Action':
				action = field['mnem']
			elif field['name'] == 'RomAddr':
				romAddr = field['mnem']

			pos += field['length']

		return (action, romAddr)

	def genAnalysisOutput(self):
		nameLine = ''
		letterLine = ''
		bitsLine = ''
		mnemLine = ''

		pos = 0
		while(True):
			field = self.getNextField(pos)
			if field == None:
				break

			fieldLen = max(len(field['name']), len(field['bits']), len(field['mnem']))
			fieldLen += 1

			formatString = '%%-%is' % fieldLen
			nameLine += formatString % field['name']
			letterLine += formatString % (len(field['bits']) * field['letter'])
			bitsLine += formatString % bitstr(field['bits'])
			mnemLine += formatString % field['mnem']

			pos += field['length']

		return nameLine + '\n' + letterLine + '\n' + bitsLine + '\n' + mnemLine



class UcodeDis(object):
	def __init__(self, ucode):
		self.ucode = ucode

	def getTriadMnem(self, num):
		triad = self.ucode.get_triad(num, negate=True)
		ops = tuple(Operation(bits) for bits in triad.cut(64, count=3))
		sw = SequenceWord(next(triad.cut(32, 3*64, count=1)))

		return (ops[0].getMnem(), ops[1].getMnem(), ops[2].getMnem(), sw.getMnem())

	def analyzeTriad(self, num):
		triad = self.ucode.get_triad(num, negate=True)
		ops = (Operation(bits) for bits in triad.cut(64, count=3))
		sw = SequenceWord(next(triad.cut(32, 3*64, count=1)))

		output = ''
		for op in ops:
			output += op.genAnalysisOutput() + '\n\n'
		output += sw.genAnalysisOutput()

		return output