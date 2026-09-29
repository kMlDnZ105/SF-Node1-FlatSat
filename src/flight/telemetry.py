import time
import math
from machine import Pin, I2C
import config

def bcd2dec(bcd): 
    return (bcd >> 4) * 10 + (bcd & 0x0F)

def parse_s16(h, l):
    v = (h << 8) | l
    return v - 65536 if v >= 32768 else v

def init_sensors(i2c):
    """Sensör donanımlarını uçuşa hazır hale getirir."""
    # 1. MPU6050 Uyandır (0x69)
    try:
        i2c.writeto_mem(config.ADDR_MPU6050, 0x6B, bytearray([0x00]))
    except: pass

    # 2. BMP580 Başlat (0x47)
    try:
        i2c.writeto_mem(config.ADDR_BMP580, 0x37, bytearray([0x80])); time.sleep_ms(10)
        i2c.writeto_mem(config.ADDR_BMP580, 0x36, bytearray([0x51])); time.sleep_ms(10)
        i2c.writeto_mem(config.ADDR_BMP580, 0x37, bytearray([0x83]))
    except: pass

    # 3. HP5883 Başlat (0x2C)
    try:
        i2c.writeto_mem(config.ADDR_HP5883, 0x0B, bytearray([0x80])); time.sleep_ms(20)
        i2c.writeto_mem(config.ADDR_HP5883, 0x0B, bytearray([0x00])); time.sleep_ms(20)
        i2c.writeto_mem(config.ADDR_HP5883, 0x09, bytearray([0x19]))
        i2c.writeto_mem(config.ADDR_HP5883, 0x0A, bytearray([0x19]))
        i2c.writeto_mem(config.ADDR_HP5883, 0x0B, bytearray([0x01]))
    except: pass

    # 4. INA219 Başlat (0x40)
    try:
        i2c.writeto_mem(config.ADDR_INA219, 0x00, bytearray([0x39, 0x9F]))
        i2c.writeto_mem(config.ADDR_INA219, 0x05, bytearray([0x10, 0x00]))
    except: pass

def read_all(i2c):
    """Tüm alt sistemleri tek seferde okuyup telemetri demeti döner."""
    # RTC Zamanı
    try:
        d = i2c.readfrom_mem(config.ADDR_DS3231, 0x00, 7)
        sec = bcd2dec(d[0] & 0x7F)
        minute = bcd2dec(d[1] & 0x7F)
        hour = bcd2dec(d[2] & 0x3F)
        day = bcd2dec(d[4] & 0x3F)
        month = bcd2dec(d[5] & 0x1F)
        year = 2000 + bcd2dec(d[6])
        t_stamp = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{sec:02d}"
    except:
        t_stamp = "2026-09-23 00:00:00"

    # BMP580
    try:
        d_bmp = i2c.readfrom_mem(config.ADDR_BMP580, 0x1D, 6)
        rt = d_bmp[0] | (d_bmp[1] << 8) | (d_bmp[2] << 16)
        if rt >= 0x800000: rt -= 0x1000000
        temp_c = rt / 65536.0
        rp = d_bmp[3] | (d_bmp[4] << 8) | (d_bmp[5] << 16)
        press_hpa = rp / 6400.0
        alt_m = 44330.0 * (1.0 - (press_hpa / 1013.25) ** 0.1903) if press_hpa > 0 else 0.0
    except:
        temp_c, press_hpa, alt_m = 0.0, 0.0, 0.0

    # MPU6050
    try:
        d_mpu = i2c.readfrom_mem(config.ADDR_MPU6050, 0x3B, 14)
        ax = parse_s16(d_mpu[0], d_mpu[1]) / 16384.0
        ay = parse_s16(d_mpu[2], d_mpu[3]) / 16384.0
        az = parse_s16(d_mpu[4], d_mpu[5]) / 16384.0
        gx = parse_s16(d_mpu[8], d_mpu[9]) / 131.0
        gy = parse_s16(d_mpu[10], d_mpu[11]) / 131.0
        gz = parse_s16(d_mpu[12], d_mpu[13]) / 131.0
    except:
        ax, ay, az, gx, gy, gz = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    # HP5883
    try:
        d_mag = i2c.readfrom_mem(config.ADDR_HP5883, 0x01, 6)
        mx = parse_s16(d_mag[1], d_mag[0])
        my = parse_s16(d_mag[3], d_mag[2])
        head = math.degrees(math.atan2(my - config.MAG_Y_OFFSET, mx - config.MAG_X_OFFSET))
        if head < 0: head += 360
    except:
        head = 0.0

    # INA219
    try:
        d_v = i2c.readfrom_mem(config.ADDR_INA219, 0x02, 2)
        v_bus = ((d_v[0] << 8 | d_v[1]) >> 3) * 0.004
        d_s = i2c.readfrom_mem(config.ADDR_INA219, 0x01, 2)
        s_val = parse_s16(d_s[0], d_s[1])
        i_ma = (s_val * 0.01) / 0.1
        p_mw = v_bus * i_ma
    except:
        v_bus, i_ma, p_mw = 0.0, 0.0, 0.0

    return t_stamp, alt_m, press_hpa, temp_c, ax, ay, az, gx, gy, gz, head, v_bus, i_ma, p_mw