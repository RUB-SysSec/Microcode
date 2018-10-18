from ucsp import *
from serial_connection import serial_connection

SERVER_ERROR_OK = 0
SERVER_ERROR_TIMEOUT = 1
SERVER_ERROR_WRONG_PACKET = 2

IA32_ISRS_NAMES = ("Division by zero", "Debug", "Non-maskable interrupt", "Breakpoint",
        "Detected overflow", "Out-of-bounds", "Invalid opcode", "No coprocessor",
        "Double fault", "Coprocessor segment overrun", "Bad TSS", "Segment not present",
        "Stack fault", "General protection fault", "Page fault", "Unknown interrupt",
        "Coprocessor fault", "Alignment check", "Machine check", "Reserved",
        "Reserved", "Reserved", "Reserved", "Reserved",
        "Reserved", "Reserved", "Reserved", "Reserved",
        "Reserved", "Reserved", "Reserved", "Reserved")

class server_ret(object):
        def __init__(self, error, ucsp_type=0, value=0):
                self.error = error
                self.ucsp_type = ucsp_type
                self.value = value

        def __str__(self):
                return self.value

class server(object):
        def __init__(self, port="/dev/ttyUSB0", gpio_str="26,24,22"):
                com = serial_connection(port, gpio_str)
                self.sc = com
                self.com = com.com                
                self.ping_data = None
                self.ping_time = None

        def recv_packet(self, timeout):
                packet = bytearray()
                pos = 0
                t0 = 0

                while(1):
                        byte = self.com.read()
                        if len(byte) != 1:
                                if t0 == 0:
                                        t0 = time.time()
                                        continue
                                elif timeout > 0 and time.time() > t0 + timeout / 2:
                                        return None
                                else:
                                        continue
                        t0 = 0
                        byte = struct.unpack('<B', byte)[0]
                        if pos < 4:
                                if byte == UCSP_SIG[pos]:
                                        packet.append(byte)
                                        pos += 1
                                else:
                                        packet = bytearray()
                                        pos = 0

                        elif pos < 8:
                                packet.append(byte)
                                if pos == 7:
                                        sig, ptype, length = struct.unpack_from('<LHH', packet)
                                        if length == 0:
                                                return packet
                                pos += 1

                        else:
                                sig, ptype, length = struct.unpack_from('<LHH', packet)
                                if pos < 8 + length:
                                        packet.append(byte)

                                        if pos == 8 + length - 1:
                                                return packet

                                        pos += 1
                return None


        def dispatch_packet(self, packet):
                if not packet or len(packet) < 8:
                        return None

                sig, ptype, length = struct.unpack_from('<LHH', packet)

                if ptype == UCSP_TYPE_PONG:
                        delta = time.time() - self.ping_time
                        corrupt = ''
                        if self.ping_data != packet[8:]:
                                corrupt = ' (data corrupt)'
                        #print('PING %u bytes: time=%0.2fms%s' % (len(packet), delta * 1000, corrupt))
                        self.ping_time = 0
                        self.ping_data = bytes()
                        return delta

                elif ptype == UCSP_TYPE_CPUID_R:
                        cpuid_str = struct.unpack_from('<%us' % len(packet[8:]), packet[8:])[0]
                        return cpuid_str

                elif ptype == UCSP_TYPE_APPLY_UCODE_R:
                        if len(packet[8:]) == 4:
                                return struct.unpack_from('<L', packet[8:])
                        # angry OS can send back 64 4 Byte words, this handles it
                        elif len(packet[8:]) == 64 * 4:
                                return struct.unpack_from('<' + 64*'L', packet[8:])
                        # this is the older behavior, only parse the first 16 words
                        else:
                                return struct.unpack_from('<LLLLLLLLLLLLLLLL', packet[8:])

                elif ptype in UCSP_OOO_PACKETS:
                        if ptype == UCSP_TYPE_OOO_OS_CRASH_R:
                                gs, fs, es, ds = struct.unpack_from('<LLLL', packet[8:])
                                edi, esi, ebp, esp = struct.unpack_from('<LLLL', packet[8:], 16)
                                ebx, edx, ecx, eax = struct.unpack_from('<LLLL', packet[8:], 32)
                                int_no, err_code = struct.unpack_from('<LL', packet[8:], 48)
                                eip, cs, eflags, fault_esp, ss = struct.unpack_from('<LLLLL', packet[8:], 56)
                                if int_no == 14:
                                        cr2 = struct.unpack_from('<L', packet[8:], 76)[0]
                                        p = 1 if err_code & 0x1 else 0;
                                        w = 1 if err_code & 0x2 else 0;
                                        u = 1 if err_code & 0x4 else 0;
                                        r = 1 if err_code & 0x8 else 0;
                                        i = 1 if err_code & 0x10 else 0;
                                try:
                                        print('CPU crashed with %i (%s), error code: 0x%X' % (int_no, IA32_ISRS_NAMES[int_no], err_code))
                                except Exception as e:
                                        print(e)
                                        print('CPU crashed with %i, error code: 0x%X' % (int_no, err_code))
                                print('gs = 0x%x, fs = 0x%x, es = 0x%x, ds = 0x%x' % (gs, fs, es, ds))
                                print('edi = 0x%x, esi = 0x%x, ebp = 0x%x, esp = 0x%x' % (edi, esi, ebp, esp))
                                print('ebx = 0x%x, edx = 0x%x, ecx = 0x%x, eax = 0x%x' % (ebx, edx, ecx, eax))
                                print('faulting: eip = 0x%x, cs = 0x%x, eflags = 0x%x, esp = 0x%x, ss = 0x%x' % (eip, cs, eflags, fault_esp, ss))
                                if int_no == 14:
                                        print('cr2 = 0x%x, p = %i, w = %i, u = %i, r = %i, i = %i' % (cr2, p, w, u, r, i))

                        elif ptype == UCSP_TYPE_OOO_MSG_R:
                                msg = struct.unpack_from('<%is' % length, packet, 8)[0]
                                print('OS: ' + msg)

                return None

        def get_packet(self, timeout, expected_ucsp_type):
                while True:
                        packet = self.recv_packet(timeout)
                        if not packet:
                                return server_ret(SERVER_ERROR_TIMEOUT)

                        sig, ptype, length = struct.unpack_from('<LHH', packet)
                        if ptype in UCSP_OOO_PACKETS:
                                self.dispatch_packet(packet)
                                continue

                        if ptype != expected_ucsp_type:
                                return server_ret(SERVER_ERROR_WRONG_PACKET, ptype)

                        value = self.dispatch_packet(packet)
                        break
                return server_ret(SERVER_ERROR_OK, ptype, value)

        def wait_for_connection(self):
                while(1):
                        self.ping_time = time.time()
                        self.com.write(ucsp.get_ping_packet(bytes(56*'A')))
                        ret = self.get_packet(1, UCSP_TYPE_PONG)

                        if ret.error == UCSP_ERROR_WRONG_PACKET:
                                return False

                        if ret.error == UCSP_ERROR_TIMEOUT:
                                continue

                        if ret.error == UCSP_ERROR_OK:
                                return True

        def send_packet(self, packet):
                if struct.unpack_from('<LH', packet, 0)[1] == UCSP_TYPE_PING:
                        self.ping_time = time.time()
                return self.com.write(packet)

        def press_pwr(self):
                return self.sc.press_pwr()

        def press_rst(self):
                return self.sc.press_rst()

        def is_on(self):
                return self.sc.is_on()

        def pwr_off(self):
                return self.sc.pwr_off()

        def pwr_on_reset(self):
                return self.sc.pwr_on_reset()

        def wait_for_ready(self):
                self.send_packet(ucsp.get_ping_packet(bytes(56*'A')))
                r = self.get_packet(1, UCSP_TYPE_PONG)
                if r.error != UCSP_ERROR_OK:
                        self.pwr_on_reset()
                        self.wait_for_connection()
                        return False
                return True