import struct
from util import *
from bitstring import *

class ucode_triad(object):
    def __init__(self, data=None, triadnum=None):
        self.ops = [Bits('uint:64=0') for i in range(3)]
        self.sw = Bits('uint:32=0')

        if data and triadnum == None:
            self.parsetriad_plain(data)
        elif data and triadnum != None:
            self.parsetriad_crypt(data, triadnum)

    def get_plain(self):
        l = [self.ops[i] for i in range(3)]
        l.append(self.sw)
        return Bits().join(l)

    def getbytes_plain(self):
        return self.get_plain().bytes

    def get_crypt(self, triadnum):
        i = triadnum * 7
        data = self.get_plain()
        ts = list(struct.unpack_from('>LLLLLLL', data.bytes, 0))
        for i in range(0,6,2):
            t = ts[i + 1]
            ts[i + 1] = ts[i]
            ts[i] = t
        s = ""
        i = triadnum * 7
        for t in ts:
            j = ROR(t, 32 - i)
            s += struct.pack('<L', j)
            i += 1
        data = Bits(bytes=s)
        return data

    def getbytes_crypt(self, triadnum):
        return self.get_crypt(triadnum).bytes

    def parsetriad_plain(self, data):
        self.ops = [i for i in data.cut(64, 0, 3*64, 3)]
        self.sw = cut(data, 32, 192)

    def parsetriad_crypt(self, data, triadnum):
        data = BitArray(data)
        i = triadnum * 7
        s = []
        for b in data.cut(32):
            b.byteswap()
            b.ror(i)
            i += 1
            s.append(b)
        for i in range(0,6,2):
            t = s[i + 1]
            s[i + 1] = s[i]
            s[i] = t
        bits = Bits().join(s)
        self.parsetriad_plain(bits)

    def __str__(self):
        s = ""
        s += "%016X %016X %016X %08X" % (self.ops[0].uint, self.ops[1].uint, self.ops[2].uint, self.sw.uint)
        return s

    def setbit_op(self, opnum, bitnum):
        self.ops[opnum] = Bits(set_bit(self.ops[opnum].uint, bitnum))

    def setbit_sw(self, bitnum):
        self.sw = Bits(set_bit(self.sw.uint, bitnum))

    def clearbit_op(self, opnum, bitnum):
        self.ops[opnum] = Bits(clear_bit(self.ops[opnum].uint, bitnum))

    def clearbit_sw(self, bitnum):
        self.sw = Bits(clear_bit(self.sw.uint, bitnum))

    def togglebit_op(self, opnum, bitnum):
        self.ops[opnum] = Bits(toggle_bit(self.ops[opnum].uint, bitnum))

    def togglebit_sw(self, bitnum):
        self.sw = Bits(toggle_bit(self.sw.uint, bitnum))

class ucode(object):
    class ucode_header(object):
        def __init__(self, data=None):
            self.stepping = None
            self.model = None
            self.family = None
            self.extmodel = None
            self.extfam = None
            self.date = None
            self.patch_id = None
            self.mpb_id = None
            self.patch_len = None
            self.init_flag = None
            self.checksum = None
            self.cpuid = None
            self.signature = None
            self.unknown1 = None
            self.unknown2 = None
            self.match_register_list = []
            if data:
                self.parseheader(data)
            else:
                self.loaddefaultheader()

        def loaddefaultheader(self):
            # build header
            header = bytearray()
            header += struct.pack('<LLHBBL', 0x02062004, 0x00000039, 0x8000, 0x0, 0x00, 0x0)
            header += struct.pack('<LLLL', 0x00000000, 0x00000000, 0x00000048, 0xaaaaaa00)
            header += struct.pack('<LLLL', 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff)
            header += struct.pack('<LLLL', 0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff)
            self.parseheader(header)

        def parseheader(self, data):
            self.date, self.patch_id, self.mpb_id, self.patch_len, self.init_flag, self.checksum = struct.unpack_from('<LLHBBL', data, 0)
            self.unknown1, self.unknown2, self.cpuid, self.signature = struct.unpack_from('<LLLL', data, 16)
            self.match_register_list = list(struct.unpack_from('<LLLLLLLL', data, 32))
            self.stepping = self.cpuid & 0xF
            self.model = (self.cpuid >> 4) & 0xF
            self.family = (self.cpuid >> 8) & 0xF
            self.extmodel = (self.cpuid >> 16) & 0xF
            self.extfam = (self.cpuid >> 20) & 0xFF

        def getheader(self, triadnum = None):
            # gen new header from vars
            # fixup triad count
            if triadnum != None:
                self.patch_len = triadnum
            header = bytearray()
            header += struct.pack('<LLHBBL', self.date, self.patch_id, self.mpb_id, self.patch_len, self.init_flag, self.checksum)
            header += struct.pack('<LLLL', self.unknown1, self.unknown2, self.cpuid, self.signature)
            for mr in self.match_register_list:
                header += struct.pack('<L', mr)
            return header

        def __str__(self):
            s = ""
            s += 'K8 ucode update header:\n'
            s += '\tDate %08x\n' % self.date
            s += '\tPatch ID %08x\n' % self.patch_id
            s += '\tMPB ID %04x\n' % self.mpb_id
            s += '\tNumber of triads %02x\n' % self.patch_len
            s += '\tInit flag %02x\n' % self.init_flag
            s += '\tChecksum %08x\n' % self.checksum
            s += '\tCPUID %08x\n' % self.cpuid
            s += '\tFamily %d, Model %d, Stepping %d, Extfam %d, Extmodel %d\n' % (self.family, self.model, self.stepping, self.extfam, self.extmodel)
            s += '\tSignature %08x\n' % self.signature

            s += 'Match register contents:\n'
            for i, mreg in enumerate(self.match_register_list):
                s += '\tMR%d %08x\n' % (i, mreg)
            return s
            
    def __init__(self, f=None):
        self.data = bytearray()
        self.header = ucode.ucode_header()
        self.triads = []
        self.ucode_update_len = 0
        if f:
            self.readucode(f)

    def pad_triads(self, newnum):
        # add eax, 0; add eax, 0; add eax, 0; SW_NEXT
        noop = Bits().join([Bits(uint = 0xffffffffffffffff, length=64), Bits(uint = 0xffffffffffffffff, length=64), Bits(uint = 0xffffffffffffffff, length=64), Bits(uint = 0xffffffff, length=32)])
        for i in range(self.header.patch_len, newnum):
            self.triads.append(ucode_triad(noop))
        self.header.patch_len = newnum

    def get_triad(self, triadnum, negate=False):
        triad = self.triads[triadnum]
        bs = Bits()
        for op in triad.ops:
            if negate:
                bs += op ^ Bits(uint=0xffffffffffffffff, length=64)
            else:
                bs += op
        bs += triad.sw
        return bs

    def set_triad(self, triadnum, triad, negate=False):
        if negate:
            s = []
            for i in triad.cut(32, 0, 32*6, 6):
                s.append(i ^ Bits(uint=0xffffffff, length=32))
            s.append(cut(triad, 32, 192))
            triad = Bits().join(s)
        if triadnum >= self.header.patch_len:
            self.pad_triads(triadnum + 1)
        self.triads[triadnum] = ucode_triad(triad)

    def set_triads(self, triads, negate=False):
        for i, triad in zip(range(70), triads.cut(32*7)):
            self.set_triad(i, triad, negate)

    def adjust_checksum(self):
        buf = self.getbytes_crypt()
        buf = buf[64:]
        length = len(buf)
        c = 0
        for i in range(int(length / 4)):
            c = (c + struct.unpack_from('<L', buf[i*4:])[0]) & 0xffffffff
        self.header.checksum = c        

    def readucode(self, f):
        data = f.read()
        self.ucode_update_len = len(data)
        self.header = ucode.ucode_header(data[:64])

        for i in range(self.header.patch_len):
            self.triads.append(ucode_triad(Bits(bytes=data[64+i*28:64+(i+1)*28]), i))

    def getbytes_crypt(self, recalc_chksum = False):
        if recalc_chksum:
            self.adjust_checksum()
        s = ""
        s += self.header.getheader(len(self.triads))
        for i, t in enumerate(self.triads):
            s += t.getbytes_crypt(i)
        return s

    def getbytes_plain(self):
        s = ""
        s += self.header.getheader()
        for i, t in enumerate(self.triads):
            s += t.getbytes_plain()
        return s

    def gettriadbytes_crypt(self, triadnum):
        return self.triads[triadnum].getbytes_crypt(triadnum)
