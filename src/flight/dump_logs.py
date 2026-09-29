import os
from machine import Pin, SPI
import config
from sd_driver import ReliableSD

print("=" * 65)
print("       KARA KUTU: PİLLİ UÇUŞ LOG DÖKÜMÜ              ")
print("=" * 65)

miso = Pin(config.PIN_MISO, Pin.IN, Pin.PULL_UP)
cs = Pin(config.PIN_CS, Pin.OUT, value=1)
sck = Pin(config.PIN_SCK)
mosi = Pin(config.PIN_MOSI)
spi = SPI(0, baudrate=config.SPI_BAUD, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)

try:
    sd = ReliableSD(spi, cs)
    vfs = os.VfsFat(sd)
    try:
        os.mount(vfs, "/sd")
    except: pass
except Exception as e:
    print(f"[HATA] SD Kart Bağlanamadı: {e}")
    raise SystemExit

try:
    with open(config.LOG_FILE_PATH, "r") as f:
        lines = f.readlines()
        
    total_pkts = len(lines) - 1
    print(f"[BAŞARILI] Toplam Kayıtlı Telemetri: {total_pkts} paket")
    print(f" -> Süre: ~{total_pkts * 0.2:.1f} saniye ({ (total_pkts * 0.2)/60:.1f} dakika)\n")
    
    print("--- CSV BAŞLIK ---")
    print(lines[0].strip())
    print("-" * 65)
    
    print("--- SON 25 UÇUŞ PAKETİ ---")
    for l in lines[-25:]:
        print(l.strip())
        
except Exception as e:
    print(f"[HATA] Dosya Okunamadı: {e}")