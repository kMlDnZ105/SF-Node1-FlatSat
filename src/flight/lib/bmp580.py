# S&F Node - Bosch BMP580 Barometer & Altimeter Driver (I2C Adres: 0x47)
import time

class BMP580:
    def __init__(self, i2c, addr=0x47):
        self.i2c = i2c
        self.addr = addr
        
        # Sensör kimlik kontrolü (0x01 register'ı 0x50 veya 0x51 döner)
        chip_id = self.i2c.readfrom_mem(self.addr, 0x01, 1)[0]
        if chip_id not in (0x50, 0x51):
            # Bazı breakout kartlarda SDO GND'ye çekilirse adres 0x46 olur
            self.addr = 0x46
        
        # OSR konfigürasyonu: Basınç ve sıcaklık için oversampling (0x36)
        self.i2c.writeto_mem(self.addr, 0x36, b'\x49')
        # ODR konfigürasyonu: 50Hz sürekli ölçüm modu (Continuous Mode) (0x37)
        self.i2c.writeto_mem(self.addr, 0x37, b'\x33')
        time.sleep_ms(20)

    def _read_raw(self):
        # Sıcaklık (0x1D..0x1F) ve Basınç (0x20..0x22) toplam 6 bayt
        data = self.i2c.readfrom_mem(self.addr, 0x1D, 6)
        
        raw_temp = data[0] | (data[1] << 8) | (data[2] << 16)
        if raw_temp > 0x7FFFFF:
            raw_temp -= 0x1000000
            
        raw_press = data[3] | (data[4] << 8) | (data[5] << 16)
        return raw_temp, raw_press

    @property
    def temperature(self):
        # Santigrat (°C) cinsinden sıcaklık
        raw_temp, _ = self._read_raw()
        return round(raw_temp / 65536.0, 2)

    @property
    def pressure(self):
        # hPa (hektoPaskal) cinsinden atmosferik basınç
        _, raw_press = self._read_raw()
        return round((raw_press / 64.0) / 100.0, 2)

    @property
    def altitude(self):
        # Standart atmosfer modeline göre yaklaşık irtifa hesabı (Metre)
        p = self.pressure
        if p <= 0: return 0.0
        return round(44330.0 * (1.0 - (p / 1013.25) ** 0.1903), 1)