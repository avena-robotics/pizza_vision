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
        self.data_register = [defaultdict(int)]

        self.app = get_server(RTUServer, self.s)
        self.flags = Flags()

        self.data_mtx = threading.Lock()

        self.handle_modbus_thread = threading.Thread(target=self.handle_request_threaded, daemon=True).start()

        @self.app.route(slave_ids=[1], function_codes=[3],
                        addresses=list(range(MB_START_DATA_VISIONSYSTEM, MB_END_DATA_VISIONSYSTEM + 1)))
        def read_data_store(slave_id, function_code, address):
            """" Return value of address. """
            # print(f'[read_data_store]: Telemetry. Address: {address}')
            if address == MB_START_DATA_VISIONSYSTEM:
                self.data_mtx.acquire()
            elif address == MB_END_DATA_VISIONSYSTEM:
                self.data_mtx.release()
            return self.data_register[0][address]

        @self.app.route(slave_ids=[1], function_codes=[16], addresses=list(range(MB_START_VISION_FLAGS, MB_END_VISION_FLAGS + 1)))
        def set_flags(slave_id, function_code, address, value):
            """" Set control words. """
            # print(f'[write_control_words]: Address: {address}, value: {value}')
            # TODO: Poprawić to
            self.flags.call_function = True

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
