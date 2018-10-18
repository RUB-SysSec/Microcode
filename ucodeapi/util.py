def ROR(x, n, bitsize=32):
    if n == 0:
        return x
    if n < 0:
        n = bitsize + n
    n = n % bitsize
    mask = (2**n) - 1
    mask_bits = x & mask
    return (x >> n) | (mask_bits << (bitsize - n))

def toggle_bit(val, i):
    return val ^ (1 << i)

def clear_bit(val, i):
    return val & (~(1 << i) )

def set_bit(val, i):
    return val | (1 << i)

def parsebitstring(val):
    val = val[:]
    if not val.startswith("0b"):
        val = "0b" + val
    val = val.replace(" ", "")
    val = int(val, 0)
    return val

def negateint(val, bitsize=64):
    for i in range(bitsize):
        val = toggle_bit(val, i)
    return val

def cut(bits, length, start):
    return next(bits.cut(length, start))