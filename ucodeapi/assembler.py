# Based on https://github.com/longld/peda (CC-BY-NC-SA)

import os
import subprocess
import re
from tempfile import NamedTemporaryFile

def bytes_iterator(bytes_):
    """
    Returns iterator over a bytestring. In Python 2, this is just a str. In
    Python 3, this is a bytes.
    Wrap this around a bytestring when you need to iterate to be compatible
    with Python 2 and Python 3.
    """
    raise Exception('Should be overriden')


def _bytes_iterator_py2(bytes_):
    """
    Returns iterator over a bytestring in Python 2.
    Do not call directly, use bytes_iterator instead
    """
    for b in bytes_:
        yield b


def _bytes_iterator_py3(bytes_):
    """
    Returns iterator over a bytestring in Python 3.
    Do not call directly, use bytes_iterator instead
    """
    for b in bytes_:
        yield bytes([b])

def to_hexstr(str_):
    """
    Convert a binary string to hex escape format
    """
    return "".join(["\\x%02x" % ord(i) for i in _bytes_iterator_py2(str_)])

def assemble(asmcode, mode=32):
    """
    Assemble ASM instructions using NASM
        - asmcode: input ASM instructions, multiple instructions are separated by ";" (String)
        - mode: 16/32/64 bits assembly
    Returns:
        - bin code (raw bytes)
    """
    asmcode = asmcode.strip('"').strip("'")
    asmcode = ("BITS %d\n" % mode) + asmcode
    infd = NamedTemporaryFile(mode="w", delete=False)
    outfd = NamedTemporaryFile(delete=False)
    iname = infd.name
    oname = outfd.name
    outfd.close()
    infd.write(asmcode)
    infd.close()
    os.system("nasm -f bin -o '%s' '%s'" % (oname, iname))
    outfd = open(oname, "rb")
    bincode = outfd.read()
    outfd.close()
    os.remove(iname)
    os.remove(oname)
    return bincode

def disassemble(bincode, mode=32):
    p = subprocess.Popen(["ndisasm", "-b", "%d" % mode, "-"], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    out = p.communicate(bincode)[0]
    return out

def nasm2shellcode(asmcode):
    if not asmcode:
        return ""

    shellcode = []
    pattern = re.compile("([0-9A-F]{8})\s*([^\s]*)\s*(.*)")

    matches = pattern.findall(asmcode)
    for line in asmcode.splitlines():
        m = pattern.match(line)
        if m:
            (addr, bytes, code) = m.groups()
            sc = '"%s"' % to_hexstr(bytes)
            shellcode += [(sc, "0x"+addr, code)]

    maxlen = max([len(x[0]) for x in shellcode])
    text = ""
    for (sc, addr, code) in shellcode:
        text += "%s # %s:    %s\n" % (sc.ljust(maxlen+1), addr, code)

    return text

if __name__ == '__main__':
    t = nasm2shellcode(disassemble(assemble("mov eax, eax; mov ebx, eax")))
    print(t)
