import bitstring as bs
from util import *

def parseval(val):
    if not val.startswith("0b"):
        val = "0b" + val

    val = val.replace(" ", "")

    val = int(val, 0)
    return val

class Mnemonic(object):
    def __init__(self, mnemonic, comment = ""):
        super(Mnemonic, self).__init__()
        self.mnemonic = mnemonic
        self.comment = comment

class Register(object):
    def __init__(self, reg8, reg16, reg32):
        super(Register, self).__init__()
        self.reg8 = reg8
        self.reg16 = reg16
        self.reg32 = reg32

    def getReg(self, size):
        if size == 8:
            return self.reg8
        elif size == 16:
            return self.reg16
        # currently we are 32bit only (I guess), so we assume 64 bit to be equal to 32 bit
        elif size == 32 or size == 64:
            return self.reg32
        else:
            raise ValueError("Ucodedecoder: Invalid operand size %u for register %s" % (size, self.reg32))

class Opcode(object):        
    def __init__(self, bits, arch):
        super(Opcode, self).__init__()
        self.bits = bits
        self.arch = arch
        self.mnemonic = ""
        self.mnemcomment = ""
        self.opbits = None

    def __str__(self):
        zx = "ZX" if self.dstzx else ""
        if self.immsrc:
            src = "0x%08X" % (self.imm)
        else:
            src = self.srcreg.getReg(32)
        s = "%s%s %s, %s" % (self.mnemonic, zx, self.dstregsized, src)
        return s

    def verbosestr(self):
        s = "Opcode (1-9): \t\t%s (0x%02X) %s\n" % (self.opbits.bin, self.opbits.uint, self.mnemonic)
        s += "Comment: \t\t%s\n" % self.mnemcomment
        s += "Destination (12-17): \t%s (0x%02X) %s (unsized: %s)\n" % (self.dstbits.bin, self.dstbits.uint, self.dstregsized, self.dst.getReg(32))
        s += "Data Size (31-33): \t%s (0x%02X) %i, zero extended: %s\n" % (self.dszbits.bin, self.dszbits.uint, self.dstsize, self.dstzx)
        s += "Immediate bit (40): \t%s\n" % (self.immbit.bin)
        s += "Immediate (48-63): \t%s 0x%08X\n" % (self.immbits.bin, self.immbits.uint)
        if not self.immsrc:
            s += "Source Reg (49-54): \t%s (0x%02X) %s\n" % (self.srcbits.bin, self.srcbits.uint, self.srcreg.getReg(32))
        else:
            try:
                s += "Source Reg (49-54): \t%s (0x%02X) %s\n" % (self.srcbits.bin, self.srcbits.uint, self.getReg(self.srcbits))
            except:
                s += "Source Reg (49-54): \t%s (0x%02X) %s\n" % (self.srcbits.bin, self.srcbits.uint, "unknown")
        s += "Full opcode: \t\t%s" % (self)
        return s

    def bitrepr(self):
        s = cut(self.bits, 1, 0).bin
        s += " " + self.opbits.bin
        s += " " + cut(self.bits, 2, 10).bin
        s += " " + self.dstbits.bin
        s += " " + cut(self.bits, 13, 18).bin
        s += " " + self.dszbits.bin
        s += " " + cut(self.bits, 6, 34).bin
        s += " " + self.immbit.bin
        s += " " + cut(self.bits, 7, 41).bin
        s += " " + self.immbits.bin
        s += "\n"
        s += "? OOOOOOOOO ?2 DDDDDD ????????????? ZZZ dddddd R ??????? IIIIIIIIIIIIIIII"
        return s
 
class Ucodedecoder(object):
    operations_k8 = {
        "000000000": ("ADD", "dst = dst + src"),
        "000000001": ("ADD", "dst = dst + src"),
        "000000010": ("ADC", "dst = dst + src + carry"),
        "000000011": ("SBC", ""),
        "000000100": ("AND", ""),
        "000000101": ("SUB", ""),
        "000000110": ("OR", ""),
        "000000111": ("SUB", ""),
        "000001000": ("NOP", ""),
        "000001001": ("RNG", ""),
        "000001010": ("RNG", ""),
        "000001011": ("ISUB", "dst = src - dst"),
        "000001100": ("RNG", ""),
        "000001101": ("ISUB", "dst = src - dst"),
        "000001110": ("RNG", ""),
        "000001111": ("ISUB", "dst = src - dst"),
        "000010000": ("SET0", ""),
        "000010001": ("ROR", "dst = dst >> src; slightly weird"),
        "000010010": ("RNG", ""),
        "000010011": ("RNG", ""),
        "000010100": ("ROR", "dst = dst >> src; slightly weird"),
        "000010101": ("SHR", ""),
        "000010110": ("ROL", ""),
        "000010111": ("ROR", ""),
        "000011000": ("ROLE", ""),
        "000011001": ("RORE", "dst = dst >> src + 1"),
        "000011010": ("ROLE", "dst = dst << src + 1"),
        "000011011": ("RORE", "dst = dst >> src + 1"),
        "000011100": ("ROLE", "dst = dst << src + 1"),
        "000011101": ("RORE", "dst = dst >> src + 1"),
        "000011110": ("ROLE", "dst = dst << src + 1"),
        "000011111": ("RORE", "dst = dst >> src + 1"),
        "000100000": ("ADDE", "dst = dst + src + 1"),
        "000100001": ("RNG", ""),
        "000100010": ("RNG", ""),
        "000100011": ("RNG", ""),
        "000100100": ("RNG", ""),
        "000100101": ("RNG", ""),
        "000100110": ("RNG", ""),
        "000100111": ("RNG", ""),
        "000101000": ("RNG", ""),
        "000101001": ("RNG", ""),
        "000101010": ("RNG", ""),
        "000101011": ("RNG", ""),
        "000101100": ("RNG", ""),
        "000101101": ("RNG", ""),
        "000101110": ("RNG", ""),
        "000101111": ("RNG", ""),
        "000110000": ("SBBE", "dst = dst + CF - src - 1"),
        "000110001": ("RNG", ""),
        "000110010": ("RNG", ""),
        "000110011": ("RNG", ""),
        "000110100": ("RNG", ""),
        "000110101": ("RNG", ""),
        "000110110": ("RNG", ""),
        "000110111": ("NOP", ""),
        "000111000": ("TCSUB", "dst = dst - src; two's complement"),
        "000111001": ("RNG", ""),
        "000111010": ("NOP", ""),
        "000111011": ("BMC", "bitmask clear?; slightly weird"),
        "000111100": ("RNG", ""),
        "000111101": ("RNG", ""),
        "000111110": ("NOP", ""),
        "000111111": ("NOP", ""),
        "001000100": ("CRASH", ""),
        "001001000": ("CRASH", ""),
        "001001100": ("CRASH", ""),
        "001010000": ("NOP", "uncertain"),
        "001010100": ("RNG", ""),
        "001011000": ("RNG", ""),
        "001011100": ("RNG", ""),
        "001100000": ("MOV", "dst = src"),
        "001110000": ("MUL", "dst = dst * src; lower 32bit"),
        "001111000": ("RNG", ""),
        "001111100": ("BMC", "bitmask clear?"),
        "010000000": ("NOP", "uncertain"),
        "010000100": ("NOP", ""),
        "010001000": ("NOP", ""),
        "010001100": ("NOP", ""),
        "010010000": ("SET0", ""),
        "010010100": ("SET0", ""),
        "010011000": ("SET0", ""),
        "010011100": ("SET0", ""),
        "010100000": ("NOP", "uncertain"),
        "010100100": ("NOP", ""),
        "010101000": ("NOP", ""),
        "010101100": ("NOP", ""),
        "010110000": ("NOP", "uncertain"),
        "010110100": ("NOP", ""),
        "010111000": ("NOP", ""),
        "010111100": ("NOP", ""),
        "011000000": ("NOP", "uncertain"),
        "011000100": ("NOP", ""),
        "011001000": ("NOP", ""),
        "011001100": ("NOP", ""),
        "011010000": ("NOP", "uncertain"),
        "011100000": ("NOP", "uncertain"),
        "011100100": ("NOP", ""),
        "011101000": ("NOP", ""),
        "011101100": ("NOP", ""),
        "011110000": ("NOP", "uncertain"),
        "100000100": ("RNG", ""),
        "100010000": ("RNG", ""),
        "100100000": ("RNG", ""),
        "100110000": ("RNG", ""),
        "101000000": ("RNG", ""),
        "101010000": ("NOP", ""),
        "101100000": ("RNG", ""),
        "101110000": ("RNG", ""),
        "110000000": ("RNG", ""),
        "110010000": ("RNG", ""),
        "110100000": ("RNG", ""),
        "110110000": ("RNG", ""),
        "111000000": ("SET0", ""),
        "111010000": ("RNG", ""),
        "111100000": ("RNG", ""),
        "111110000": ("RNG", ""),


        "111111100": ("UNK1", ""),
        "101010110": ("UNK2", ""),
        "001001110": ("UNK3", ""),
        "101011000": ("UNK4", ""),
        "101100110": ("UNK5", ""),
        "111101100": ("UNK6", ""),
        "001000011": ("UNK7", ""),
        "001000111": ("UNK8", ""),
        "111111110": ("UNK9", ""),
        "010100010": ("UNK10", ""),
        "100000000": ("UNK11", ""),
        "010000111": ("UNK12", ""),
        "011010100": ("UNK13", ""),
        "011010101": ("UNK14", ""),
        "001101000": ("UNK15", ""),
        "011010011": ("UNK16", ""),
        "010100011": ("UNK17", ""),
        "001111111": ("UNK18", ""),
        "010100101": ("UNK19", ""),
        "001111111": ("UNK18", ""),
        "001111111": ("UNK18", ""),
        "001111111": ("UNK18", ""),
    }

    registers_k8 = {
        "000000" : ("AL", "AX", "EAX"),
        "000001" : ("CL", "CX", "ECX"),
        "000010" : ("DL", "DX", "EDX"),
        "000011" : ("BL", "BX", "EBX"),
        "000100" : ("AH", "SP", "ESP"),
        "000101" : ("CH", "BP", "EBP"),
        "000110" : ("DH", "SI", "ESI"),
        "000111" : ("BH", "DI", "EDI"),

        "001000" : ("t1L", "t1", "t1"),
        "001001" : ("t2L", "t2", "t2"),
        "001010" : ("t3L", "t3", "t3"),
        "001011" : ("t4L", "t4", "t4"),
        "001100" : ("t1H", "t5", "t5"),
        "001101" : ("t2H", "t6", "t6"),
        "001110" : ("t3H", "PC", "PC"),
        "001111" : ("t4H", "t0", "t0"),
        "010000" : ("t8L", "t8", "t8"),
        "010001" : ("t9L", "t9", "t9"),
        "010010" : ("t10L", "t10", "t10"),
        "010011" : ("t11L", "t11", "t11"),
        "010100" : ("t8H", "t12", "t12"),
        "010101" : ("t9H", "t13", "t13"),
        "010110" : ("t10H", "t14", "t14"),
        "010111" : ("t11H", "t15", "t15"),
        "011000" : ("t16", "t16", "t16"),
        "011001" : ("t17", "t17", "t17"),
        "011010" : ("t18", "t18", "t18"),
        "011011" : ("t19", "t19", "t19"),
        "011100" : ("t20", "t20", "t20"),
        "011101" : ("t21", "t21", "t21"),
        "011110" : ("t22", "t22", "t22"),
        "011111" : ("t23", "t23", "t23"),
        "100000" : ("t24", "t24", "t24"),
        "100001" : ("t25", "t25", "t25"),
        "100010" : ("t26", "t26", "t26"),
        "100011" : ("t27", "t27", "t27"),
        "100100" : ("t28", "t28", "t28"),
        "100101" : ("t29", "t29", "t29"),
        "100110" : ("t30", "t30", "t30"),
        "100111" : ("t31", "t31", "t31"),
        "101000" : ("regm", "regm", "regm"),
        "101001" : ("regm", "regm", "regm"),
        "101010" : ("t34", "t34", "t34"),
        "101011" : ("EDI?", "EDI?", "EDI?"),
        "101100" : ("ESI?", "ESI?", "ESI?"),
        "101101" : ("t37", "t37", "t37"),
        "101110" : ("t38", "t38", "t38"),
        "101111" : ("t39", "t39", "t39"),
        "110000" : ("t40", "t40", "t40"),
        "110001" : ("t41", "t41", "t41"),
        "110010" : ("t42", "t42", "t42"),
        "110011" : ("t43", "t43", "t43"),
        "110100" : ("t44", "t44", "t44"),
        "110101" : ("t45", "t45", "t45"),
        "110110" : ("t46", "t46", "t46"),
        "110111" : ("t47", "t47", "t47"),
        "111000" : ("t48", "t48", "t48"),
        "111001" : ("t49", "t49", "t49"),
        "111010" : ("t50", "t50", "t50"),
        "111011" : ("t51", "t51", "t51"),
        "111100" : ("t52", "t52", "t52"),
        "111101" : ("t53", "t53", "t53"),
        "111110" : ("t54", "t54", "t54"),
        "111111" : ("t55", "t55", "t55")
    }

    dsz_k8 = {
        #bits   :  (size, zero extend)
        "000" : (8, False),
        "001" : (16, False),
        "010" : (32, False),
        "011" : (64, False),
        "100" : (8, True),
        "101" : (16, True),
        "110" : (32, True),
        "111" : (64, True)
    }

    def __init__(self, arch = "k8", plaintext = True):
        super(Ucodedecoder, self).__init__()
        self.operations = {}
        self.registers = {}
        self.dsz = {}
        self.plaintext = plaintext
        if arch == "k8":
            for k,v in self.operations_k8.items():
                self.operations[parseval(k)] = Mnemonic(*v)
            for k,v in self.registers_k8.items():
                self.registers[parseval(k)] = Register(*v)
            for k,v in self.dsz_k8.items():
                self.dsz[parseval(k)] = v
        else:
            raise ValueError("Ucodedecoder: Unsupported architecture: %s" % arch)
        self.arch = arch

    def getOp(self, opbits):
        try:
            return self.operations[opbits.uint]
        except:
            raise ValueError("Ucodedecoder: Unsupported operation: %s" % (opbits.bin))

    def getReg(self, regbits):
        try:
            return self.registers[regbits.uint]
        except:
            raise ValueError("Ucodedecoder: Unsupported register: %s" % (regbits.bin))

    def getDsz(self, dszbits):
        try:
            return self.dsz[dszbits.uint]
        except:
            raise ValueError("Ucodedecoder: Unsupported DSz: %s" % (dszbits.bin))

    def decode(self, arg):
        if type(arg) is bs.Bits:
            if arg.len != 64:
                raise ValueError("Ucodedecoder: Invalid bitstring length %u, only 64 bit are supported" % arg.len)
            bits = arg
        elif type(arg) is int or type(arg) is long:
            bits = bs.Bits(uint=arg, length=64)
        else:
            raise ValueError("Ucodedecoder: Unsupported argument type %s, supported are Bitstring.bits, int and long" % type(arg))
        if not self.plaintext:
            all1 = bs.Bits(uint=0xffffffffffffffff, length=64)
            bits = all1 ^ bits
        opc = Opcode(bits, self.arch)
        if self.arch == "k8":

            opbits = next(bits.cut(9, 1))
            mnem = self.getOp(opbits)
            opc.mnemonic = mnem.mnemonic
            opc.mnemcomment = mnem.comment
            opc.opbits = opbits

            dstbits = next(bits.cut(6, 12))
            reg = self.getReg(dstbits)
            opc.dst = reg
            opc.dstbits = dstbits

            dszbits = next(bits.cut(3, 31))
            dsz = self.getDsz(dszbits)
            opc.dstsize = dsz[0]
            opc.dstzx = dsz[1]
            opc.dszbits = dszbits
            opc.dstregsized = opc.dst.getReg(opc.dstsize)

            immbit = next(bits.cut(1, 40))
            isimm = immbit.all(False)
            opc.immbit = immbit
            opc.immsrc = isimm
            immbits = next(bits.cut(16, 48))
            opc.immbits = immbits
            srcbits = next(bits.cut(6, 49))
            opc.srcbits = srcbits
            if isimm:
                opc.imm = immbits.uint
                opc.srcreg = None
            else:
                opc.srcreg = self.getReg(srcbits)
                opc.imm = None
            return opc
