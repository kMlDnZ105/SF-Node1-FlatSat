# SF Node 1 (FlatSat) — Pin ve Veri Yolu Haritası

Referans: `SF1-FLT-TR-001` Tablo 1 (Donanım Envanteri ve Veri Yolu Konfigürasyonu)

## Uçuş Bilgisayarı — Raspberry Pi Pico (RP2040)

| Alt Sistem | Bileşen | Veri Yolu / Pin | Adres / Parametre | Görev |
|---|---|---|---|---|
| OBC | Raspberry Pi Pico (RP2040) | Sistem Çekirdeği | 133 MHz, MicroPython v1.2x | Uçuş kontrolü, telemetri paketleme |
| COMM | AI-Thinker Ra-02 (SX1278) | SPI1 (GP10–GP15) | 433,0 MHz, SF7/SF9, BW 125 kHz | İki yönlü LoRa telemetri/telekomut |
| COMM (RF) | Ra-02 RF çıkış katı ve anten | RF çıkışı (SMA/tel) | +14 dBm (25 mW) | Monopol (çeyrek dalga tel) anten |
| EPS | 3,7 V Li-Po (3000 mAh) | Güç Hattı | TP4056 koruma devresi | Ana enerji kaynağı |
| EPS Sensör | INA219 | I2C0 (GP4/GP5) | 0x40 | Gerilim, akım, güç tüketimi ölçümü |
| Navigasyon | MPU6050 (6-DOF IMU) | I2C0 (GP4/GP5) | 0x69 (AD0 → 3,3 V) | 3 eksen ivmeölçer + jiroskop |
| Yönelim | HP5883 / QMC5883L | I2C0 (GP4/GP5) | 0x2C | 3 eksen manyetometre |
| Termal/Baro | Bosch BMP580 | I2C0 (GP4/GP5) | 0x47 | Barometrik irtifa ve sıcaklık |
| Zamanlama | Maxim DS3231 | I2C0 (GP4/GP5) | 0x68 (TCXO) | UTC zaman damgası referansı |
| Depolama | MicroSD Modülü | SPI0 (GP16–GP19) | SPI 1 MHz, VfsFat | Yerel telemetri kara kutu kaydı |

## Yer İstasyonu Köprüsü — Raspberry Pi Pico (Pico 2)

| Bileşen | Veri Yolu / Pin | Görev |
|---|---|---|
| Ra-02 (SX1278) | SPI (aynı LoRa telsizi) | Yer istasyonu tarafında RF alım |
| USB Seri (COM5) | 115200 Baud, özel GUI | RF paket çözümü ve PC'ye aktarım |

## I2C0 Veri Yolu Adresleme Notu

Fabrika çıkışı MPU6050 I2C adresi (0x68), DS3231 RTC'nin adresiyle
çakışmaktaydı. Çözüm: MPU6050 `AD0` pini 3,3 V'a çekilerek adres `0x69`'a
ötelendi. Beş I2C0 cihazı (0x2C, 0x40, 0x47, 0x68, 0x69) artık çakışmasız
adreslenmektedir.

## Görsel Referanslar

- Sistem blok diyagramı: `SF1-FLT-TR-001` Şekil 2
- Breadboard entegrasyon fotoğrafları: `hardware/photos/`
