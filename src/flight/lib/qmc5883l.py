# S&F Node - GY-271 (QMC5883L) 3-Axis Magnetometer Driver (I2C Adres: 0x0D)
import struct
import math

class QMC5883L:
    def __init__(self, i2c, addr=0x0D):
        self.i2c = i2c
        self.addr = addr
        # Sensör reset & periyot register'ı (0x0B -> 0x01)
        self.i2c.writeto_mem(self.addr, 0x0B, b'\x01')
        # Sürekli okuma modu: 200Hz ODR, 8 Gauss skala, 512 OSR (0x09 -> 0x1D)
        self.i2c.writeto_mem(self.addr, 0x09, b'\x1D')

    def read_raw(self):
        # 6 bayt ham veri oku: X_LSB, X_MSB, Y_LSB, Y_MSB, Z_LSB, Z_MSB (Little-endian)
        data = self.i2c.readfrom_mem(self.addr, 0x00, 6)
        x, y, z = struct.unpack('<hhh', data)
        return x, y, z

    @property
    def mag(self):
        # Gauss biriminde X, Y, Z vektörleri (±8G için çarpan: 1/3000)
        x, y, z = self.read_raw()
        return (x / 3000.0, y / 3000.0, z / 3000.0)

    @property
    def heading(self):
        # X ve Y eksenlerinden pusula açısı hesabı (0 - 360 derece)
        x, y, _ = self.read_raw()
        heading_rad = math.atan2(y, x)
        heading_deg = math.degrees(heading_rad)
        if heading_deg < 0:
            heading_deg += 360.0
        return round(heading_deg, 2)