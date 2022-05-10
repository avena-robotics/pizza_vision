import os
import threading
import struct
import time
from collections import defaultdict

from serial import Serial, SerialTimeoutException, serialutil
from umodbus.server.serial import get_server
from umodbus.server.serial.rtu import RTUServer
from umodbus.client.serial.redundancy_check import CRCError

# Adresy danych w rejestrach
MB_START_DATA_VISIONSYSTEM = 1
MB_END_DATA_VISIONSYSTEM = 12

MB_START_VISION_FLAGS = 13
MB_END_VISION_FLAGS = 20

# flagi od eventów

class Flags:
    call_function = False
    send_data = False


class ModbusServer:

    def __init__(self):
        self.s = Serial(
            # adres
            port=os.path.expanduser('~')+'/dev/vision_slave',
            baudrate=115200,
            bytesize=serialutil.EIGHTBITS,
            parity=serialutil.PARITY_NONE,
            stopbits=serialutil.STOPBITS_ONE,
            timeout=0.1
        )
        self.s.flush()
        self.data_store = defaultdict(int)

        # Tworze sobie rejestr na dane
        self.data_register = [0] * 12

        self.app = get_server(RTUServer, self.s)
        self.flags = Flags()

        self.data_mtx = threading.Lock()

        self.handle_modbus_thread = threading.Thread(target=self.handle_request_threaded, daemon=True).start()

        @self.app.route(slave_ids=[1], function_codes=[3],
                        addresses=list(range(MB_START_DATA_VISIONSYSTEM, MB_END_DATA_VISIONSYSTEM + 1)))
        def read_position(slave_id, function_code, address):
            """" Return value of address. """
            # print(address)
            if address == MB_START_DATA_VISIONSYSTEM:
                self.data_mtx.acquire()
            elif address == MB_END_DATA_VISIONSYSTEM:
                self.data_mtx.release()
            return self.data_register[address-1]

        @self.app.route(slave_ids=[1], function_codes=[5], addresses=[13])
        def set_trigger(slave_id, function_code, address, value):
            if value:
                self.flags.call_function = True
            return 0

        @self.app.route(slave_ids=[1], function_codes=[3], addresses=[14])
        def dupa(slave_id, function_code, address):
            buf = 0
            if self.flags.send_data:
                buf = 1
                self.flags.send_data = False
            return buf
        
        


    def handle_request_threaded(self):
        while True:
            time.sleep(0.05)
            try:
                self.app.serve_once()
            except (CRCError, struct.error) as e:
                print("Can't handle request: {0}".format(e))
            except SerialTimeoutException as e:
                print('[ERROR]: SerialTimeoutException', e)
            except ValueError as e:
                # print('[ERROR]: ValueError', e)
                pass


if __name__ == '__main__':
    ms = ModbusServer()
    while True:
        time.sleep(1)