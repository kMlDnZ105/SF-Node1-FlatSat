# S&F Node - DS3231 RTC Driver (I2C Adres: 0x68)
class DS3231:
    def __init__(self, i2c, addr=0x68):
        self.i2c = i2c
        self.addr = addr

    def _dec2bcd(self, val):
        return (val // 10) << 4 | (val % 10)

    def _bcd2dec(self, val):
        return (val >> 4) * 10 + (val & 0x0F)

    def datetime(self, dt=None):
        if dt is None:
            # 0x00'dan 7 bayt oku: [sn, dk, sa, gun_no, gun, ay, yil]
            data = self.i2c.readfrom_mem(self.addr, 0x00, 7)
            ss = self._bcd2dec(data[0] & 0x7F)
            mm = self._bcd2dec(data[1] & 0x7F)
            hh = self._bcd2dec(data[2] & 0x3F)
            day = self._bcd2dec(data[4] & 0x3F)
            month = self._bcd2dec(data[5] & 0x1F)
            year = self._bcd2dec(data[6]) + 2000
            return (year, month, day, hh, mm, ss)
        else:
            # Saati ayarla: (year, month, day, hh, mm, ss)
            year, month, day, hh, mm, ss = dt
            buf = bytearray([
                self._dec2bcd(ss),
                self._dec2bcd(mm),
                self._dec2bcd(hh),
                1,
                self._dec2bcd(day),
                self._dec2bcd(month),
                self._dec2bcd(year - 2000)
            ])
            self.i2c.writeto_mem(self.addr, 0x00, buf)

    def get_iso_time(self):
        y, m, d, hh, mm, ss = self.datetime()
        return f"{y:04d}-{m:02d}-{d:02d}T{hh:02d}:{mm:02d}:{ss:02d}Z"