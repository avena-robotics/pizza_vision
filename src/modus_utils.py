import asyncio
from data import DataStructure
import modbus_server
import random
import time

# TODO: Owrapować funkcjonalnosc systemu wizyjnego w jedna funkcje


async def handle_flags(mb_server: modbus_server.ModbusServer):
    while True:
        if mb_server.flags.call_function:
            mb_server.flags.call_function = False
            # Jakas funkcja, ktora bedzie wykonywac to wszystko
            print("Kalkuluje pozycje!")
            calculate_and_send_position(mb_server)
            mb_server.flags.send_data = True
        await asyncio.sleep(0.1)


def calculate_and_send_position(mb_server: modbus_server.ModbusServer):
    # Z owrapowanej funkcji zwroce datastructure
    time.sleep(1)
    data_structure = DataStructure(1, 2, 3, random.randint(1, 10))
    data_structure.parse_to_modbus(mb_server)
    print(mb_server.data_register)


async def main():
    mb_serv = modbus_server.ModbusServer()
    tasks = []
    tasks.append(asyncio.create_task(handle_flags(mb_serv)))
    g = await asyncio.gather(*tasks)

a = asyncio.run(main())