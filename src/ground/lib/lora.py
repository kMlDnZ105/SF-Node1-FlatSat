# ===================================================================
# S&F Node - Ra-02 (SX1278) 433 MHz LoRa Donanım Sürücüsü (SPI)
# DOSYA: lib/lora.py
# ÖZELLİKLER: CRC Denetimi, RSSI & SNR Ölçümü, Tam Kesme Temizleme
# ===================================================================
from machine import Pin, SPI
import time

class SX1278:
    def __init__(self, spi, cs_pin, rst_pin, dio0_pin, freq=433.0):
        self.spi = spi
        self.cs = Pin(cs_pin, Pin.OUT, value=1)
        self.rst = Pin(rst_pin, Pin.OUT, value=1)
        self.dio0 = Pin(dio0_pin, Pin.IN)
        self.freq = freq

        self.reset()

        # 1. Silikon Kimlik Kontrolü (Register 0x42 == 0x12 olmalıdır)
        version = self._read_reg(0x42)
        if version != 0x12:
            raise OSError(f"LoRa SX1278 cipi hatta bulunamadi (Okunan: {hex(version)})")

        # 2. Uyku Moduna Al ve LoRa Modunu Aktifleştir (RegOpMode 0x01 -> 0x80)
        self._write_reg(0x01, 0x80)
        time.sleep_ms(10)

        # 3. Standby Modu (RegOpMode 0x01 -> 0x81)
        self._write_reg(0x01, 0x81)

        # 4. Frekans Ayarı (433.0 MHz)
        frf = int((self.freq * 1000000.0) / 61.035)
        self._write_reg(0x06, (frf >> 16) & 0xFF)
        self._write_reg(0x07, (frf >> 8) & 0xFF)
        self._write_reg(0x08, frf & 0xFF)

        # 5. Çıkış Gücü (PA_BOOST: +14 dBm seviyesinde dengelendi)
        self._write_reg(0x09, 0x8C)

        # 6. Modem Ayarları:
        # RegModemConfig1 (0x1D): BW 125kHz (0x70) + CR 4/5 (0x02) + Explicit Header (0x00) -> 0x72
        self._write_reg(0x1D, 0x72)
        
        # RegModemConfig2 (0x1E): SF7 (0x70) + CRC Aktif (0x04) -> 0x74
        self._write_reg(0x1E, 0x74)

        # RegModemConfig3 (0x26): Otomatik AGC devrede -> 0x04
        self._write_reg(0x26, 0x04)

        # 7. FIFO Taban Adresleri (Tx ve Rx için 0x00)
        self._write_reg(0x0E, 0x00)
        self._write_reg(0x0F, 0x00)

        # 8. Tüm eski kesme bayraklarını temizle
        self._write_reg(0x12, 0xFF)

    def reset(self):
        self.rst.value(0)
        time.sleep_ms(10)
        self.rst.value(1)
        time.sleep_ms(10)

    def _write_reg(self, reg, val):
        self.cs.value(0)
        self.spi.write(bytearray([reg | 0x80, val]))
        self.cs.value(1)

    def _read_reg(self, reg):
        self.cs.value(0)
        self.spi.write(bytearray([reg & 0x7F]))
        val = self.spi.read(1)[0]
        self.cs.value(1)
        return val

    def send(self, payload):
        # Gönderme (TX) Rutini
        self._write_reg(0x01, 0x81)          # Standby
        self._write_reg(0x12, 0xFF)          # Kesmeleri temizle
        self._write_reg(0x0D, 0x00)          # FIFO işaretçisini TX tabanına al

        raw_data = payload.encode("utf-8") if isinstance(payload, str) else payload
        self._write_reg(0x22, len(raw_data)) # Paket uzunluğu

        # Veriyi FIFO'ya yaz
        self.cs.value(0)
        self.spi.write(bytearray([0x00 | 0x80]))
        self.spi.write(raw_data)
        self.cs.value(1)

        # TX Modunu tetikle (RegOpMode -> 0x83)
        self._write_reg(0x01, 0x83)

        # Gönderim tamamlanana kadar bekle (TxDone: 0x08)
        timeout = 200
        while not (self._read_reg(0x12) & 0x08):
            time.sleep_ms(10)
            timeout -= 1
            if timeout <= 0:
                break

        # Kesmeyi temizle ve Standby'a dön
        self._write_reg(0x12, 0xFF)
        self._write_reg(0x01, 0x81)

    def set_rx_mode(self):
        # Kesmeleri temizle, FIFO işaretçisini sıfırla ve RX moduna geç
        self._write_reg(0x12, 0xFF)
        self._write_reg(0x0D, 0x00)
        self._write_reg(0x01, 0x85)          # Continuous RX Modu

    def receive(self):
        irq_flags = self._read_reg(0x12)

        # RxDone bayrağı (0x40) yandı mı?
        if irq_flags & 0x40:
            crc_error = irq_flags & 0x20     # PayloadCrcError biti (0x20)

            # RSSI ve SNR değerlerini hesapla
            rssi = self._read_reg(0x1A) - 164
            snr_raw = self._read_reg(0x19)
            snr = (snr_raw - 256 if snr_raw > 127 else snr_raw) * 0.25

            # Kesme bayraklarını anında temizle
            self._write_reg(0x12, 0xFF)

            # Paket bozuksa reddet
            if crc_error:
                print(f"[RF-UYARI] CRC Hatalı Paket Düştü! Sinyal: {rssi} dBm | SNR: {snr} dB")
                return None

            # Paketin boyutunu ve FIFO'daki başlangıç adresini al
            nb_bytes = self._read_reg(0x13)
            current_addr = self._read_reg(0x10)
            self._write_reg(0x0D, current_addr)

            # FIFO'dan paketi oku
            self.cs.value(0)
            self.spi.write(bytearray([0x00 & 0x7F]))
            packet_data = self.spi.read(nb_bytes)
            self.cs.value(1)

            try:
                decoded = packet_data.decode("utf-8")
                return decoded
            except Exception:
                # UTF-8 çözülemezse ham bayt olarak bas
                return f"[HAM]: {str(packet_data)}"

        return None