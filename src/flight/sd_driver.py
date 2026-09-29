import time
from machine import Pin, SPI

class ReliableSD:
    def __init__(self, spi, cs):
        self.spi = spi
        self.cs = cs
        self.cs.value(1)
        self.init_card()

    def _cmd(self, cmd, arg, crc):
        self.cs.value(0)
        self.spi.write(b'\xFF')
        pkt = bytearray([
            0x40 | cmd,
            (arg >> 24) & 0xFF,
            (arg >> 16) & 0xFF,
            (arg >> 8) & 0xFF,
            arg & 0xFF,
            crc
        ])
        self.spi.write(pkt)
        for _ in range(100):
            res = self.spi.read(1, 0xFF)[0]
            if not (res & 0x80):
                return res
        return 0xFF

    def init_card(self):
        self.cs.value(1); self.spi.write(b'\xFF' * 16); time.sleep_ms(50)
        if self._cmd(0, 0, 0x95) != 0x01: raise OSError("SD Reset Hatasi")
        self.cs.value(1); self.spi.write(b'\xFF')
        self._cmd(8, 0x1AA, 0x87); self.spi.read(4, 0xFF); self.cs.value(1); self.spi.write(b'\xFF')
        
        ready = False
        for _ in range(250):
            self._cmd(55, 0, 0xFF); self.cs.value(1); self.spi.write(b'\xFF')
            if self._cmd(41, 0x40000000, 0xFF) == 0x00:
                ready = True; self.cs.value(1); self.spi.write(b'\xFF'); break
            self.cs.value(1); self.spi.write(b'\xFF'); time.sleep_ms(10)
        if not ready: raise OSError("Uyanma zaman asimi")

        self._cmd(58, 0, 0xFF); ocr = self.spi.read(4, 0xFF); self.cs.value(1); self.spi.write(b'\xFF')
        self.cdv = 1 if (ocr[0] & 0x40) else 512

    def readblocks(self, b, buf):
        for i in range(len(buf) // 512):
            addr = (b + i) * self.cdv
            if self._cmd(17, addr, 0xFF) != 0x00:
                self.cs.value(1); self.spi.write(b'\xFF')
                raise OSError("CMD17 Hatasi")
            
            token = 0xFF
            for _ in range(4000):
                x = self.spi.read(1, 0xFF)[0]
                if x != 0xFF: token = x; break
            if token != 0xFE:
                self.cs.value(1); self.spi.write(b'\xFF')
                raise OSError("Okuma Token Hatasi")

            off = i * 512
            self.spi.readinto(memoryview(buf)[off:off + 512], 0xFF)
            self.spi.read(2, 0xFF)
            self.cs.value(1); self.spi.write(b'\xFF')

    def writeblocks(self, b, buf):
        for i in range(len(buf) // 512):
            addr = (b + i) * self.cdv
            if self._cmd(24, addr, 0xFF) != 0x00:
                self.cs.value(1); self.spi.write(b'\xFF')
                raise OSError("CMD24 Hatasi")

            # Start Token (0xFE)
            self.spi.write(b'\xFF\xFE')
            off = i * 512
            self.spi.write(memoryview(buf)[off:off + 512])
            self.spi.write(b'\xFF\xFF')

            # Yanıt Onayı
            resp = 0xFF
            for _ in range(100):
                r = self.spi.read(1, 0xFF)[0]
                if r != 0xFF:
                    resp = r
                    break

            if (resp & 0x1F) != 0x05 and resp not in (0xCA, 0xE5, 0x00):
                self.cs.value(1); self.spi.write(b'\xFF')
                raise OSError(f"Yazma Reddedildi: {hex(resp)}")

            # Meşguliyetin (Busy = 0x00) Bitmesini Bekle
            t0 = time.ticks_ms()
            while self.spi.read(1, 0xFF)[0] == 0x00:
                if time.ticks_diff(time.ticks_ms(), t0) > 1000:
                    self.cs.value(1); self.spi.write(b'\xFF')
                    raise OSError("Yazma Zaman Asimi")

            self.cs.value(1); self.spi.write(b'\xFF')

    def ioctl(self, op, arg):
        if op == 4: return 31116288
        if op == 5: return 512
        return 0