import serial
import re
import operator
from functools import reduce
DEBUG=False
from time import sleep

reply_pattern = re.compile(r"\x02..(.*)\x03.", re.DOTALL)
standard_device='0011'
EOT = '\x04'
STX = '\x02'
ENQ = '\x05'
ETX = '\x03'
ACK = '\x06'
NAK = '\x15'

def checksum(message):
    bcc = (reduce(operator.xor, map(ord,message)))
    return chr(bcc)

class Eurotherm(object):
        def __init__(self, serial_device, baudrate = 9600):
                self.device = standard_device
                # timeout: 110 ms to get all answers.
                self.s = serial.Serial(serial_device,
                                        baudrate = baudrate,
                                        bytesize=7,
                                        parity='E',
                                        stopbits=1,
                                        timeout=0.11,
                                        write_timeout=1)
                self._expect_len = 120

        def send_read_param(self, param):
                self.s.write(bytes(EOT + self.device + param + ENQ,'UTF-8'))
                #sleep(0.05)
                
        def read_param(self, param):
                self.s.flushInput()
                self.send_read_param(param)
                answer = self.s.read(self._expect_len).decode('UTF-8')
                m = reply_pattern.search(answer)
                if m is None:
                        # Reading _expect_len bytes was not enough...
                        answer += self.s.read(200).decode('UTF-8')
                        m = reply_pattern.search(answer)
                if m is not None:
                        self._expect_len = len(answer)
                        return m.group(1)
                else:
                        print("received:", repr(answer))
                        return None

        def write_param(self, mnemonic, data):
                if len(mnemonic) > 2:
                        raise ValueError
                bcc = checksum(mnemonic + data + ETX)
                mes = EOT+self.device+STX+mnemonic+data+ETX+bcc
                if DEBUG:
                        for i in  mes:
                                print(i,hex(ord(i)))
                self.s.flushInput()
                self.s.write(bytes(mes,'UTF-8'))
                sleep(0.05)
                answer = self.s.read(1).decode('UTF-8')
                # print "received:", repr(answer)
                if answer == "":
                        # raise IOError("No answer from device")
                        return None
                return answer[-1] == ACK

        def get_current_temperature(self):
                temp = self.read_param('PV')
                if temp is None:
                    temp = "0"
                return temp

        def set_temperature(self, temperature):
                return self.write_param('SL', str(temperature))

        def get_setpoint_temperature(self):
                return self.read_param('SL')
