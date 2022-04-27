import struct


# Taki datastructure każdy musi sobie przygtować

class DataStructure:

    def __init__(self, x, y, z, yaw):
        self._X = x
        self._Y = y
        self._Z = z
        self._Yaw = yaw

    def parse_to_modbus(self, modbus_server):

        x_b = struct.pack(">f", self._X)
        y_b = struct.pack(">f", self._Y)
        z_b = struct.pack(">f", self._Z)
        yaw_b = struct.pack(">f", self._Yaw)

        x_b_2s = struct.unpack(">hh", x_b)
        y_b_2s = struct.unpack(">hh", y_b)
        z_b_2s = struct.unpack(">hh", z_b)
        yaw_b_2s = struct.unpack(">hh", yaw_b)

        with modbus_server.data_mtx:
            modbus_server.data_register[0:2] = x_b_2s
            modbus_server.data_register[2:4] = y_b_2s
            modbus_server.data_register[4:6] = z_b_2s
            modbus_server.data_register[6:8] = yaw_b_2s


