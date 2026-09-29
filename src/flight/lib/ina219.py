# S&F Node - INA219 Power/Current Monitor Driver (I2C Adres: 0x40)
class INA219:
    def __init__(self, i2c, addr=0x40):
        self.i2c = i2c
        self.addr = addr
        # 32V, 2A aralığı ve 12-bit ADC konfigürasyonu
        self.i2c.writeto_mem(self.addr, 0x00, b'\x39\x9F')
        # 0.1 Ohm şönt direnci için kalibrasyon
        self.i2c.writeto_mem(self.addr, 0x05, b'\x10\x00')

    def _read_word(self, reg):
        data = self.i2c.readfrom_mem(self.addr, reg, 2)
        val = int.from_bytes(data, 'big')
        return val - 65536 if val > 32767 else val

    @property
    def bus_voltage(self):
        # Bara gerilimi (Volt) - Register 0x02
        raw = int.from_bytes(self.i2c.readfrom_mem(self.addr, 0x02, 2), 'big') >> 3
        return raw * 0.004

    @property
    def current(self):
        # Çekilen anlık akım (mA) - Register 0x04
        return self._read_word(0x04) * 0.1

    @property
    def power(self):
        # Anlık güç tüketimi (mW)
        return self.bus_voltage * self.current