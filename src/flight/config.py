# AVİYONİK SİSTEM MERKEZİ KONFİGÜRASYON DOSYASI

# I2C0 Veriyolu (GP4 / GP5)
PIN_SDA = 4
PIN_SCL = 5
I2C_FREQ = 100_000

# I2C Aygıt Adresleri
ADDR_HP5883  = 0x2C   # Manyetometre / Pusula
ADDR_INA219  = 0x40   # Güç Ölçüm Katı
ADDR_BMP580  = 0x47   # Barometre / Altimetre
ADDR_DS3231  = 0x68   # Gerçek Zamanlı Saat (RTC)
ADDR_MPU6050 = 0x69   # 6-Eksen IMU (AD0 = 3.3V)

# SPI0 MicroSD Veriyolu
PIN_MISO = 16
PIN_CS   = 17
PIN_SCK  = 18
PIN_MOSI = 19
SPI_BAUD = 400_000

# Telemetri ve Uçuş Ayarları
TELEMETRY_RATE_MS = 200    # 5 Hz (200 ms aralık)
LOG_FILE_PATH = "/sd/flight_telemetry.csv"

# Manyetometre Ofsetleri (Kalibrasyon)
MAG_X_OFFSET = 3339.0
MAG_Y_OFFSET = 2619.0