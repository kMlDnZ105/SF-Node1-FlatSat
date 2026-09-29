from machine import Pin, I2C
import config

i2c = I2C(0, scl=Pin(config.PIN_SCL), sda=Pin(config.PIN_SDA), freq=config.I2C_FREQ)

def dec2bcd(dec): 
    return ((dec // 10) << 4) | (dec % 10)

def set_time(year, month, day, hour, minute, second):
    buf = bytearray([
        0x00,
        dec2bcd(second),
        dec2bcd(minute),
        dec2bcd(hour),
        0x03, # Çarşamba
        dec2bcd(day),
        dec2bcd(month),
        dec2bcd(year - 2000)
    ])
    i2c.writeto(config.ADDR_DS3231, buf)
    print(f"[OK] DS3231 Saati Güncellendi: {year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}")

# Güncel zamana göre ayarla:
set_time(2026, 9, 23, 21, 20, 0)