from bitstring import *

OP_TYPE_REG = 0x0
OP_TYPE_IMM = 0x1
OP_TYPE_MEM = 0x2
OP_TYPE_CC  = 0x3

k10_opclasses = (
{'mnem':'reg',  'bits':'000'},
{'mnem':'ld',  'bits':'001'},
{'mnem':'st',  'bits':'010'},
)

def getClassBitsByMnem(mnem):
	return Bits(bin=next((c['bits'] for c in k10_opclasses if c['mnem'] == mnem)))

def getClassMnemByBits(bits):
	return next((c['mnem'] for c in k10_opclasses if Bits(bin=c['bits']) == bits), 'NA')

k10_operations = (
{'mnem':'add',  'bits':'000000000'},
{'mnem':'or',   'bits':'000000001'},
{'mnem':'adc',  'bits':'000000010'},
{'mnem':'sbb',  'bits':'000000011'},
{'mnem':'and',  'bits':'000000100'},
{'mnem':'sub',  'bits':'000000101'},
{'mnem':'xor',  'bits':'000000110'},
{'mnem':'cmp',  'bits':'000000111'},
{'mnem':'test', 'bits':'000001000'},

{'mnem':'rll',  'bits':'000010000'},
{'mnem':'rrl',  'bits':'000010001'},
{'mnem':'sll',  'bits':'000010100'},
{'mnem':'srl',  'bits':'000010101'},

{'mnem':'writepc','bits':'001000000'}, # x86 jump, works only at OP2
{'mnem':'jmp',  'bits':'001000000'},   # alias, decode SpecOp as RegOp for simplicity

{'mnem':'mov',  'bits':'001100000'},
{'mnem':'mul1s','bits':'001110000'}, # works only at OP0
{'mnem':'mul1u','bits':'001110001'},
{'mnem':'muleh','bits':'001110010'}, # verify
{'mnem':'mulel','bits':'001110011'}, # verify
{'mnem':'mul',  'bits':'001110000'}, # alias
{'mnem':'imul', 'bits':'001110001'}, # alias

{'mnem':'ld'   ,'bits':'001111111'},
{'mnem':'st'   ,'bits':'101010000'},

{'mnem':'lea'  ,'bits':'110001101'}, # has special handling, see ucodeas for details

{'mnem':'bswap','bits':'111000000'},
{'mnem':'not',  'bits':'111110101'},
{'mnem':'crash','bits':'111111111'},
{'mnem':'div1', 'bits':'001111010'},
{'mnem':'div2', 'bits':'001111100'},

{'mnem':'jcc','bits':'0101'},
{'mnem':'branchcc','bits':'0101'}
)

def getOprnBitsByMnem(mnem):
	return Bits(bin=next((o['bits'] for o in k10_operations if o['mnem'] == mnem)))

def getOprnMnemByBits(bits):
	return next((o['mnem'] for o in k10_operations if Bits(bin=o['bits']) == bits), 'NA')

reg_ops = ['add', 'or', 'adc', 'sbb', 'and', 'sub', 'xor', 'cmp', 'test', 'rll', 'rrl', 'sll', 'srl', 'mov', 'mul', 'imul', 'bswap', 'not', 'writepc', 'jmp', 'div1', 'div2', 'lea']
ldst_ops = ['ld', 'st']
br_ops = ['jcc', 'branchcc']

# positional operation constraints
op_constraints = {'mul': 0, 'imul:': 0, 'writepc': 2, 'jmp': 2}


# weird ops:
# 001110111
# 001111100
# 001111110 mov?
# 101001100 muleh? / div1?
# 101001101 mulel? / div2?
# 101010100
# 101010101

k10_regs = (
# general purpose x86 registers
{'mnem':('al',  'ax',    'eax',  'rax' ), 'bits':'000000'},
{'mnem':('cl',   'cx',   'ecx',  'rcx' ), 'bits':'000001'},
{'mnem':('dl',   'dx',   'edx',  'rdx' ), 'bits':'000010'},
{'mnem':('bl',   'bx',   'ebx',  'rbx' ), 'bits':'000011'},
{'mnem':('ah',   'sp',   'esp',  'rsp' ), 'bits':'000100'},
{'mnem':('ch',   'bp',   'ebp',  'rbp' ), 'bits':'000101'},
{'mnem':('dh',   'si',   'esi',  'rsi' ), 'bits':'000110'},
{'mnem':('bh',   'di',   'edi',  'rdi' ), 'bits':'000111'},

# microcode registers, general purpose (maybe x86_64 r0-r7)
{'mnem':('t1l',  't1w',  't1d',  't1q' ), 'bits':'001000'},
{'mnem':('t2l',  't2w',  't2d',  't2q' ), 'bits':'001001'},
{'mnem':('t3l',  't3w',  't3d',  't3q' ), 'bits':'001010'},
{'mnem':('t4l',  't4w',  't4d',  't4q' ), 'bits':'001011'},
{'mnem':('t1h',  't5w',  't5d',  't5q' ), 'bits':'001100'},
{'mnem':('t2h',  't6w',  't6d',  't6q' ), 'bits':'001101'},
{'mnem':('t3h',  't7w',  't7d',  't7q' ), 'bits':'001110'},
{'mnem':('t4h',  't8w',  't8d',  't8q' ), 'bits':'001111'},

# microcode registers, preset values
{'mnem':('t9l',  't9w',  't9d',  't9q' ), 'bits':'010000'}, # near pcd
{'mnem':('t10l', 't10w', 't10d', 't10q'), 'bits':'010001'}, # diff of *1) and *2)
{'mnem':('t11l', 't11w', 't11d', 't11q'), 'bits':'010010'}, # changing value
{'mnem':('t12l', 't12w', 't12d', 't12q'), 'bits':'010011'}, # changing value
{'mnem':('t9h' , 't13w', 't13d', 't13q'), 'bits':'010100'},
{'mnem':('t10h', 't14w', 't14d', 't14q'), 'bits':'010101'}, # static value
{'mnem':('t11h', 't15w', 't15d', 't15q'), 'bits':'010110'}, # static value
{'mnem':('t12h', 't16w', 't16d', 't16q'), 'bits':'010111'}, # static value

# constants and byte registers
{'mnem':('t17b', 't17w', 't17d', 't17q'), 'bits':'011000'},
{'mnem':('t18b', 't18w', 't18d', 't18q'), 'bits':'011001'},
{'mnem':('t19b', 't19w', 't19d', 't19q'), 'bits':'011010'},
{'mnem':('t20b', 't20w', 't20d', 't20q'), 'bits':'011011'}, # static value
{'mnem':('t21b', 't21w', 't21d', 't21q'), 'bits':'011100'}, # static value
{'mnem':('t22b', 't22w', 't22d', 't22q'), 'bits':'011101'}, # static value
{'mnem':('t23b', 't23w', 't23d', 't23q'), 'bits':'011110'},
{'mnem':('t24b', 't24w', 't24d', 't24q'), 'bits':'011111'}, # static value

{'mnem':('t25b', 't25w', 't25d', 't25q'), 'bits':'100000'},
{'mnem':('t26b', 't26w', 't26d', 't26q'), 'bits':'100001'},
{'mnem':('t27b', 't27w', 't27d', 't27q'), 'bits':'100010'},
{'mnem':('t28b', 't28w', 't28d', 't28q'), 'bits':'100011'},
{'mnem':('t29b', 't29w', 't29d', 't29q'), 'bits':'100100'},
{'mnem':('t30b', 't30w', 't30d', 't30q'), 'bits':'100101'},
{'mnem':('t31b', 't31w', 't31d', 't31q'), 'bits':'100110'},
{'mnem':('t32b', 't32w', 't32d', 't32q'), 'bits':'100111'},
{'mnem':('regmb4', 'regmw4', 'regmd4', 'regmq4'), 'bits':'101000'},	# regm
{'mnem':('regmb5', 'regmw5', 'regmd5', 'regmq5'), 'bits':'101001'},	# regm
{'mnem':('t35b', 't35w', 't35d', 't35q'), 'bits':'101010'},
{'mnem':('regmb7', 'regmw7', 'regmd7', 'regmq7'), 'bits':'101011'}, # nop
{'mnem':('regmb6', 'regmw6', 'regmd6', 'regmq6'), 'bits':'101100'}, # regm
{'mnem':('t38b', 't38w', 't38d', 't38q'), 'bits':'101101'},
{'mnem':('t39b', 't39w', 't39d', 't39q'), 'bits':'101110'},
{'mnem':('t40b', 't40w', 't40d', 't40q'), 'bits':'101111'},

{'mnem':('t41b', 't41w', 't41d', 't41q'), 'bits':'110000'},
{'mnem':('t42b', 't42w', 't42d', 't42q'), 'bits':'110001'},
{'mnem':('t43b', 't43w', 't43d', 't43q'), 'bits':'110010'},
{'mnem':('t44b', 't44w', 't44d', 't44q'), 'bits':'110011'},
{'mnem':('t45b', 't45w', 't45d', 't45q'), 'bits':'110100'},
{'mnem':('t46b', 't46w', 't46d', 't46q'), 'bits':'110101'},
{'mnem':('t47b', 't47w', 't47d', 't47q'), 'bits':'110110'},
{'mnem':('t48b', 't48w', 't48d', 't48q'), 'bits':'110111'},

{'mnem':('pcb',  'pcw',  'pcd',  'pcq'),  'bits':'111000'}, # next decode PC
{'mnem':('t50b', 't50w', 't50d', 't50q'), 'bits':'111001'},
{'mnem':('t51b', 't51w', 't51d', 't51q'), 'bits':'111010'}, # near pcd
{'mnem':('t52b', 't52w', 't52d', 't52q'), 'bits':'111011'},
{'mnem':('t53b', 't53w', 't53d', 't53q'), 'bits':'111100'}, # static value
{'mnem':('t54b', 't54w', 't54d', 't54q'), 'bits':'111101'},
{'mnem':('t55b', 't55w', 't55d', 't55q'), 'bits':'111110'}, # static value
{'mnem':('t56b', 't56w', 't56d', 't56q'), 'bits':'111111'}
)

def getRegBitsByMnem(mnem):
	return next(r['bits'] for r in k10_regs if mnem in r['mnem'])

def getRegMnemByBits(bits, sizeBits):
	mnems = next((r['mnem'] for r in k10_regs if Bits(bin=r['bits']) == bits), None)
	if mnems == None:
		return 'NA'
	return mnems[sizeBits.uint & 3]

k10_cc = (
{'mnem':'False',	'bits':'00000'},
{'mnem':'ECF',		'bits':'00010'},
{'mnem':'EZF',		'bits':'00100'},
{'mnem':'SZnZF',	'bits':'00110'},
{'mnem':'MSTRZ',	'bits':'01000'},
{'mnem':'STRZ',		'bits':'01010'},
{'mnem':'MSTRC',	'bits':'01100'},
{'mnem':'STRZnZF',	'bits':'01110'},
{'mnem':'OF',		'bits':'10000'},
{'mnem':'CF',		'bits':'10010'},
{'mnem':'ZF',		'bits':'10100'},
{'mnem':'CvZF',		'bits':'10110'},
{'mnem':'SF',		'bits':'11000'},
{'mnem':'PF',		'bits':'11010'},
{'mnem':'SxOF',		'bits':'11100'},
{'mnem':'SxOvZF',	'bits':'11110'},

{'mnem':'True',		'bits':'00001'},
{'mnem':'nECF',		'bits':'00011'},
{'mnem':'nEZF',		'bits':'00101'},
{'mnem':'nSZnZF',	'bits':'00111'},
{'mnem':'nMSTRZ',	'bits':'01001'},
{'mnem':'nSTRZ',	'bits':'01011'},
{'mnem':'nMSTRC',	'bits':'01101'},
{'mnem':'nSTRZnZF',	'bits':'01111'},
{'mnem':'nOF',		'bits':'10001'},
{'mnem':'nCF',		'bits':'10011'},
{'mnem':'nZF',		'bits':'10101'},
{'mnem':'nCvZF',	'bits':'10111'},
{'mnem':'nSF',		'bits':'11001'},
{'mnem':'nPF',		'bits':'11011'},
{'mnem':'nSxOF',	'bits':'11101'},
{'mnem':'nSxOvZF',	'bits':'11111'}
)

def getCondBitsByMnem(mnem):
	return Bits(bin=next((c['bits'] for c in k10_cc if c['mnem'] == mnem)))

def getCondMnemByBits(bits):
	return next((c['mnem'] for c in k10_cc if Bits(bin=c['bits']) == bits), 'NA')

k10_segregs = (
{'mnem':'es',  'bits':'0000'}, # arch seg regs
{'mnem':'cs',  'bits':'0001'},
{'mnem':'ss',  'bits':'0010'},
{'mnem':'ds',  'bits':'0011'},
{'mnem':'fs',  'bits':'0100'},
{'mnem':'gs',  'bits':'0101'},
{'mnem':'hs',  'bits':'0110'}, # temp seg reg
{'mnem':'rs',  'bits':'0111'}, # reserved seg reg
{'mnem':'ts1', 'bits':'1000'}, # rable seg regs, GDT and LDT
{'mnem':'ts2', 'bits':'1001'},
{'mnem':'ls',  'bits':'1010'}, # linear seg reg
{'mnem':'ms',  'bits':'1011'}, # ucode seg reg
{'mnem':'os1', 'bits':'1100'}, # effective seg regs
{'mnem':'os2', 'bits':'1101'},
{'mnem':'os3', 'bits':'1110'},
{'mnem':'os4', 'bits':'1111'},
)

def getSegBitsByMnem(mnem):
	return Bits(bin=next((s['bits'] for s in k10_segregs if s['mnem'] == mnem)))

def getSegMnemByBits(bits):
	return next((s['mnem'] for s in k10_segregs if Bits(bin=s['bits']) == bits), 'NA')

k10_swactions = (
{'mnem':'complete',  'bits':'001'},
{'mnem':'branch'  ,  'bits':'010'},
{'mnem':'next'    ,  'bits':'111'}
)

def getSwActionBitsByMnem(mnem):
	return Bits(bin=next((a['bits'] for a in k10_swactions if a['mnem'] == mnem)))

def getSwActionMnemByBits(bits):
	return next((a['mnem'] for a in k10_swactions if Bits(bin=a['bits']) == bits), 'NA')