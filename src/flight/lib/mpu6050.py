# S&F Node - MPU6050 MicroPython Driver
class MPU6050:
    def __init__(self, i2c, addr=0x68):
        self.i2c = i2c
        self.addr = addr
        # Sensörü uyku modundan çıkar (Power Management Register 0x6B)
        self.i2c.writeto_mem(self.addr, 0x6B, b'\x00')

    def _read_word(self, reg):
        data = self.i2c.readfrom_mem(self.addr, reg, 2)
        val = int.from_bytes(data, 'big')
        return val - 65536 if val > 32767 else val

    @property
    def accel(self):
        # ±2g ölçeği: 16384 LSB/g
        ax = self._read_word(0x3B) / 16384.0
        ay = self._read_word(0x3D) / 16384.0
        az = self._read_word(0x3F) / 16384.0
        return (ax, ay, az)

    @property
    def gyro(self):
        # ±250 °/s ölçeği: 131 LSB/(°/s)
        gx = self._read_word(0x43) / 131.0
        gy = self._read_word(0x45) / 131.0
        gz = self._read_word(0x47) / 131.0
        return (gx, gy, gz)

    @property
    def temperature(self):
        # Dahili çip sıcaklığı (°C)
        raw_temp = self._read_word(0x41)
        return (raw_temp / 340.0) + 36.53