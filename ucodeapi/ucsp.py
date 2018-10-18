import time
import struct
import collections
import itertools

UCSP_TYPE_PING = 1
UCSP_TYPE_PONG = 2
UCSP_TYPE_CPUID = 3
UCSP_TYPE_CPUID_R = 4
UCSP_TYPE_SET_UCODE = 5
UCSP_TYPE_SET_UCODE_R = 6
UCSP_TYPE_PATCH_UCODE = 7
UCSP_TYPE_PATCH_UCODE_R = 8
UCSP_TYPE_APPLY_UCODE = 9
UCSP_TYPE_APPLY_UCODE_R = 10
UCSP_TYPE_EXECUTE_CODE = 11
UCSP_TYPE_EXECUTE_CODE_R = 12
UCSP_TYPE_OOO_OS_CRASH_R = 14
UCSP_TYPE_OOO_MSG_R = 16
UCSP_TYPE_EXECUTE_CODE_NOUPDATE = 18

UCSP_OOO_PACKETS = (UCSP_TYPE_OOO_OS_CRASH_R, UCSP_TYPE_OOO_MSG_R)

UCSP_SIG = (0xDE, 0xAD, 0xBE, 0xEF)

UCSP_ERROR_OK = 0
UCSP_ERROR_TIMEOUT = 1
UCSP_ERROR_WRONG_PACKET = 2

MATCH_REG0_OFFSET = 32
MATCH_REG1_OFFSET = 36
MATCH_REG2_OFFSET = 40
MATCH_REG3_OFFSET = 44
MATCH_REG4_OFFSET = 48
MATCH_REG5_OFFSET = 52
MATCH_REG6_OFFSET = 56
MATCH_REG7_OFFSET = 60

class ucsp(object):

        @staticmethod
        def get_empty_packet(packet_type):
                return struct.pack('<BBBBHH', UCSP_SIG[0], UCSP_SIG[1], UCSP_SIG[2], UCSP_SIG[3], packet_type, 0) 

        @staticmethod
        def get_packet(packet_type, data):
                return struct.pack('<BBBBHH', UCSP_SIG[0], UCSP_SIG[1], UCSP_SIG[2], UCSP_SIG[3], packet_type, len(data)) + data

        @staticmethod
        def get_ping_packet(echo):
                return ucsp.get_packet(UCSP_TYPE_PING, echo)

        @staticmethod
        def get_cpuid_packet():
                return ucsp.get_empty_packet(UCSP_TYPE_CPUID)
                
        @staticmethod
        def get_ucode_packet():
                ucode = open('u1.bin', 'rb').read()
                return ucsp.get_ucode_packet(ucode)

        @staticmethod
        def get_ucode_packet(ucode):
                return ucsp.get_packet(UCSP_TYPE_SET_UCODE, ucode)
                
        @staticmethod
        def get_patch_ucode_packet(offset, value):        
                payload = struct.pack('<LL', offset, value)
                return ucsp.get_packet(UCSP_TYPE_PATCH_UCODE, payload)
                
        @staticmethod
        def get_apply_ucode_packet():
                return ucsp.get_empty_packet(UCSP_TYPE_APPLY_UCODE)

        @staticmethod
        def get_execute_code_packet(code):
                return ucsp.get_packet(UCSP_TYPE_EXECUTE_CODE, code)

        @staticmethod
        def get_execute_code_noupdate_packet():
                return ucsp.get_empty_packet(UCSP_TYPE_EXECUTE_CODE_NOUPDATE)