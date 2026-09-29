# S&F Node - Zırhlı SD Kart Sürücüsü (Timeout Korumalı)
from micropython import const
import time

_CMD_TIMEOUT = const(100)
_R1_IDLE_STATE = const(1 << 0)

class SDCard:
    def __init__(self, spi, cs):
        self.spi = spi
        self.cs = cs
        self.cmdbuf = bytearray(6)
        self.dummybuf = bytearray(512)
        for i in range(512):
            self.dummybuf[i] = 0xFF
        self.dummybuf_token = bytearray(1)
        self.dummybuf_token[0] = 0xFF

        self.cs.init(self.cs.OUT, value=1)
        self.spi.init(baudrate=100000, polarity=0, phase=0)
        self.init_card()

    def _cmd(self, cmd, arg, crc, final=0):
        self.cmdbuf[0] = 0x40 | cmd
        self.cmdbuf[1] = arg >> 24
        self.cmdbuf[2] = arg >> 16
        self.cmdbuf[3] = arg >> 8
        self.cmdbuf[4] = arg
        self.cmdbuf[5] = crc
        self.cs(0)
        self.spi.write(self.cmdbuf)
        for i in range(_CMD_TIMEOUT):
            res = self.spi.read(1)[0]
            if not (res & 0x80):
                for j in range(final):
                    self.spi.write(self.dummybuf_token)
                return res
        return -1

    def init_card(self):
        for i in range(16):
            self.spi.write(self.dummybuf_token)
            
        # CMD0: Donanım yoksa hemen hata fırlat, sistemi kilitleme
        card_ok = False
        for i in range(5):
            if self._cmd(0, 0, 0x95) == _R1_IDLE_STATE:
                card_ok = True
                break
        if not card_ok:
            raise OSError("MicroSD kart hattan yanit vermedi")

        # CMD8 ve ACMD41
        self._cmd(8, 0x1AA, 0x87, 4)
        for i in range(50):
            self._cmd(55, 0, 0)
            if self._cmd(41, 0x40000000, 0) == 0:
                break
            time.sleep_ms(20)

        self.spi.init(baudrate=10000000)
        self.cs(1)
        self.spi.write(self.dummybuf_token)

    def readblocks(self, block_num, buf):
        self.cs(0)
        cmd = 17 if len(buf) == 512 else 18
        if self._cmd(cmd, block_num, 0) != 0:
            self.cs(1)
            raise OSError(5)
            
        for i in range(len(buf) // 512):
            timeout = 1000
            while self.spi.read(1)[0] != 0xFE:
                timeout -= 1
                if timeout <= 0:
                    self.cs(1)
                    raise OSError("Okuma zamanaşımı")
            self.spi.readinto(memoryview(buf)[i*512:(i+1)*512])
            self.spi.read(2)
        self.cs(1)
        self.spi.write(self.dummybuf_token)

    def writeblocks(self, block_num, buf):
        self.cs(0)
        cmd = 24 if len(buf) == 512 else 25
        if self._cmd(cmd, block_num, 0) != 0:
            self.cs(1)
            raise OSError(5)
        for i in range(len(buf) // 512):
            self.spi.write(b'\xFE')
            self.spi.write(memoryview(buf)[i*512:(i+1)*512])
            self.spi.write(b'\xFF\xFF')
            if (self.spi.read(1)[0] & 0x1F) != 0x05:
                self.cs(1)
                raise OSError(5)
            while self.spi.read(1)[0] == 0:
                pass
        self.cs(1)
        self.spi.write(self.dummybuf_token)

    def ioctl(self, op, arg):
        if op == 4: return 512
        if op == 5: return 2048
        return 0