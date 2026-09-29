import time
import sys
import select
from machine import Pin, SPI
from lib.lora import SX1278
import config

# SPI1: LoRa Donanım Hattı
spi_lora = SPI(
    1, baudrate=5_000_000, polarity=0, phase=0,
    sck=Pin(config.LORA_SCK),
    mosi=Pin(config.LORA_MOSI),
    miso=Pin(config.LORA_MISO)
)

# LoRa Modülünü Başlat (Ra-02 / SX1278)
lora = SX1278(spi_lora, config.LORA_CS, config.LORA_RST, config.LORA_DIO0, freq=config.LORA_FREQ)
lora.set_rx_mode()

print("[YER KÖPRÜSÜ] LoRa Dinleme Modunda Başlatıldı.")

# Bilgisayardan (GUI'den) gelecek USB seri komutları için yoklama
poll_obj = select.poll()
poll_obj.register(sys.stdin, select.POLLIN)

while True:
    # 1. Downlink: Havadan Telemetri Geldi mi?
    pkt = lora.receive()
    if pkt:
        print(pkt)  # USB kablosundan doğrudan GUI'ye akar

    # 2. Uplink: Bilgisayardan Komut Geldi mi?
    if poll_obj.poll(0):
        try:
            cmd = sys.stdin.readline().strip()
            if cmd:
                lora.send(cmd)
                lora.set_rx_mode()  # Gönderim bitince hemen tekrar dinlemeye dön
        except:
            pass

    time.sleep_ms(5)