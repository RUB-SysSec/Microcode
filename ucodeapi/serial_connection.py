import time
import serial
import RPi.GPIO as GPIO
import struct
import collections
import itertools

class serial_connection(object):
        #
        # singleton pattern, since we only have 1 connection
        #
        class __serial_connection:
                def __init__(self, port="/dev/ttyUSB0", gpio_str="26,24,22"):
                        # initialize GPIO
                        GPIO.setwarnings(False)
                        gpios = gpio_str.split(",")
                        self.GPIO_PWR = int(gpios[0])
                        self.GPIO_RST = int(gpios[1])
                        self.GPIO_PWI = int(gpios[2])
                        GPIO.setmode(GPIO.BOARD)
                        GPIO.setup(self.GPIO_PWR, GPIO.OUT)
                        GPIO.output(self.GPIO_PWR, GPIO.LOW)
                        GPIO.setup(self.GPIO_RST, GPIO.OUT)
                        GPIO.output(self.GPIO_RST, GPIO.LOW)
                        GPIO.setup(self.GPIO_PWI, GPIO.IN)
                        self.com = serial.Serial(port=port, baudrate=38400, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=0.5)        
                def press_pwr(self):
                        GPIO.output(self.GPIO_PWR, GPIO.HIGH)
                        time.sleep(0.1)
                        GPIO.output(self.GPIO_PWR, GPIO.LOW)

                def press_rst(self):
                        GPIO.output(self.GPIO_RST, GPIO.HIGH)
                        time.sleep(0.1)
                        GPIO.output(self.GPIO_RST, GPIO.LOW)

                def is_on(self):
                        hi = GPIO.input(self.GPIO_PWI)
                        if hi:
                                return False
                        else:
                                return True

                def pwr_off(self):
                        if self.is_on(): 
                                self.press_pwr()

                def pwr_on_reset(self):
                        if self.is_on():
                                self.press_rst()
                        else:
                                self.press_pwr()


        m_instance = None

        def __new__(cls, port="/dev/ttyUSB0", gpio_str="26,24,22"):
                if not serial_connection.m_instance:
                        serial_connection.m_instance = serial_connection.__serial_connection(port, gpio_str)
                return serial_connection.m_instance

        def com(self):
                return self.m_instance.com
        