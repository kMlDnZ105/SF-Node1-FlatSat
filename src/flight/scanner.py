from machine import Pin, I2C
import config

print("=" * 50)
print("       I2C VERİYOLU DONANIM TARAYICI           ")
print("=" * 50)

i2c = I2C(0, scl=Pin(config.PIN_SCL), sda=Pin(config.PIN_SDA), freq=config.I2C_FREQ)
devices = i2c.scan()
hex_devs = [hex(d) for d in devices]

print(f"Tespit Edilen Aygıtlar: {hex_devs}\n")

expected = {
    config.ADDR_HP5883:  "HP5883 Pusula",
    config.ADDR_INA219:  "INA219 Güç Katı",
    config.ADDR_BMP580:  "BMP580 Barometre",
    config.ADDR_DS3231:  "DS3231 RTC Saat",
    config.ADDR_MPU6050: "MPU6050 IMU"
}

all_ok = True
for addr, name in expected.items():
    if addr in devices:
        print(f"  [OK] {hex(addr)} -> {name}")
    else:
        print(f"  [!] {hex(addr)} -> {name} BULUNAMADI!")
        all_ok = False

if all_ok:
    print("\n[BAŞARILI] Tüm alt sistemler I2C barasında eksiksiz!")
else:
    print("\n[UYARI] Eksik sensör var, kablolamayı kontrol et.")