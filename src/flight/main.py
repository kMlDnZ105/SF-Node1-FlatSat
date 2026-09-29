import time
import math
import os
import gc
from machine import Pin, SPI, I2C

# ==============================================================================
# 1. TEMEL HAVACILIK TANIMLARI & GÖSTERGE
# ==============================================================================
CALLSIGN = "TB2CDF"
LOG_FILE = "/sd/flight_telemetry.csv"

# Heartbeat LED
try:
    led = Pin("LED", Pin.OUT)
except:
    led = Pin(25, Pin.OUT)

# Açılış sinyali (3 flaş)
for _ in range(3):
    led.value(1); time.sleep_ms(100)
    led.value(0); time.sleep_ms(100)

print("\n" + "="*50)
print(f"[OBC] {CALLSIGN} AVİYONİK UÇUŞ BİLGİSAYARI BAŞLATILIYOR")
print("="*50)

# ==============================================================================
# 2. YARDIMCI DÖNÜŞÜM FONKSİYONLARI
# ==============================================================================
def bcd2dec(bcd):
    return (bcd >> 4) * 10 + (bcd & 0x0F)

def parse_s16(h, l):
    v = (h << 8) | l
    return v - 65536 if v >= 32768 else v

# ==============================================================================
# 3. I2C DONANIM & SENSÖR AĞI BAŞLATMA
# ==============================================================================
ADDR_BMP580  = 0x47
ADDR_MPU6050 = 0x69
ADDR_DS3231  = 0x68
ADDR_HP5883  = 0x2C
ADDR_INA219  = 0x40

i2c = None
try:
    i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
    active_addrs = [hex(x) for x in i2c.scan()]
    print(f"[I2C] Aktif Donanımlar: {active_addrs}")

    # 1. MPU6050 Uyandır (0x69)
    try:
        i2c.writeto_mem(ADDR_MPU6050, 0x6B, bytearray([0x00]))
    except: pass

    # 2. BMP580 Başlat (0x47)
    try:
        i2c.writeto_mem(ADDR_BMP580, 0x37, bytearray([0x80])); time.sleep_ms(10)
        i2c.writeto_mem(ADDR_BMP580, 0x36, bytearray([0x51])); time.sleep_ms(10)
        i2c.writeto_mem(ADDR_BMP580, 0x37, bytearray([0x83]))
    except: pass

    # 3. HP5883 Manyetometre Başlat (0x2C)
    try:
        i2c.writeto_mem(ADDR_HP5883, 0x0B, bytearray([0x80])); time.sleep_ms(20)
        i2c.writeto_mem(ADDR_HP5883, 0x0B, bytearray([0x00])); time.sleep_ms(20)
        i2c.writeto_mem(ADDR_HP5883, 0x09, bytearray([0x19]))
        i2c.writeto_mem(ADDR_HP5883, 0x0A, bytearray([0x19]))
        i2c.writeto_mem(ADDR_HP5883, 0x0B, bytearray([0x01]))
    except: pass

    # 4. INA219 Güç Monitörü Başlat (0x40)
    try:
        i2c.writeto_mem(ADDR_INA219, 0x00, bytearray([0x39, 0x9F]))
        i2c.writeto_mem(ADDR_INA219, 0x05, bytearray([0x10, 0x00]))
    except: pass

    print("[SENSÖR] Tüm alt sistemler yapılandırıldı.")
except Exception as e:
    print(f"[HATA] I2C Hattı Başlatılamadı: {e}")

# ==============================================================================
# 4. MICROSD KART BAĞLANTISI (SPI0)
# ==============================================================================
sd_available = False
sd_file = None
try:
    from sd_driver import ReliableSD
    spi_sd = SPI(0, baudrate=1_000_000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(19), miso=Pin(16, Pin.IN, Pin.PULL_UP))
    cs_sd = Pin(17, Pin.OUT, value=1)
    sd_dev = ReliableSD(spi_sd, cs_sd)
    vfs = os.VfsFat(sd_dev)
    try: os.mount(vfs, "/sd")
    except: pass

    try:
        os.stat(LOG_FILE)
        file_exists = True
    except OSError:
        file_exists = False

    sd_file = open(LOG_FILE, "a")
    if not file_exists:
        sd_file.write("PKT_ID,UTC_TIME,IRTIFA_M,BASINC_HPA,SICAKLIK_C,AX,AY,AZ,GX,GY,GZ,PUSULA_DEG,GERILIM_V,AKIM_MA,GUC_MW\n")
        sd_file.flush()
    sd_available = True
    print("[DEPOLAMA] MicroSD kart hazır.")
except Exception as e:
    print(f"[UYARI] MicroSD başlatılamadı: {e}")

# ==============================================================================
# 5. LORA TELSİZ SÜRÜCÜSÜ (SPI1)
# ==============================================================================
lora = None
try:
    from lib.lora import SX1278
    spi_lora = SPI(1, baudrate=5_000_000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11), miso=Pin(12))
    # cs=13, rst=14, dio0=15, freq=433.0 MHz
    lora = SX1278(spi_lora, 13, 14, 15, freq=433.0)
    print("[HABERLEŞME] Ra-02 (SX1278) LoRa hazır.")
except Exception as e:
    print(f"[HATA] LoRa başlatılamadı: {e}")

packet_counter = 0
print("[SİSTEM] 1 Hz Canlı Telemetri Döngüsü Başlatıldı...\n")

# ==============================================================================
# 6. ANA GÖREV DÖNGÜSÜ (1 Hz)
# ==============================================================================
while True:
    t_start = time.ticks_ms()
    packet_counter += 1
    led.value(1)

    # 1. RTC Canlı Saat Okuma (DS3231: 0x68)
    t_stamp = "2026-09-24 00:00:00"
    if i2c:
        try:
            d = i2c.readfrom_mem(ADDR_DS3231, 0x00, 7)
            sec = bcd2dec(d[0] & 0x7F)
            minute = bcd2dec(d[1] & 0x7F)
            hour = bcd2dec(d[2] & 0x3F)
            day = bcd2dec(d[4] & 0x3F)
            month = bcd2dec(d[5] & 0x1F)
            year = 2000 + bcd2dec(d[6])
            t_stamp = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{sec:02d}"
        except:
            pass

    # 2. Barometre & Sıcaklık Okuma (BMP580: 0x47)
    temp_c, press_hpa, alt_m = 0.0, 0.0, 0.0
    if i2c:
        try:
            d_bmp = i2c.readfrom_mem(ADDR_BMP580, 0x1D, 6)
            rt = d_bmp[0] | (d_bmp[1] << 8) | (d_bmp[2] << 16)
            if rt >= 0x800000: rt -= 0x1000000
            temp_c = rt / 65536.0

            rp = d_bmp[3] | (d_bmp[4] << 8) | (d_bmp[5] << 16)
            press_hpa = rp / 6400.0
            alt_m = 44330.0 * (1.0 - (press_hpa / 1013.25) ** 0.1903) if press_hpa > 0 else 0.0
        except:
            pass

    # 3. İvmeölçer & Jiroskop Okuma (MPU6050: 0x69)
    ax, ay, az, gx, gy, gz = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    if i2c:
        try:
            d_mpu = i2c.readfrom_mem(ADDR_MPU6050, 0x3B, 14)
            ax = parse_s16(d_mpu[0], d_mpu[1]) / 16384.0
            ay = parse_s16(d_mpu[2], d_mpu[3]) / 16384.0
            az = parse_s16(d_mpu[4], d_mpu[5]) / 16384.0
            gx = parse_s16(d_mpu[8], d_mpu[9]) / 131.0
            gy = parse_s16(d_mpu[10], d_mpu[11]) / 131.0
            gz = parse_s16(d_mpu[12], d_mpu[13]) / 131.0
        except:
            pass

    # 4. Manyetometre / Pusula Okuma (HP5883: 0x2C)
    head = 0.0
    if i2c:
        try:
            d_mag = i2c.readfrom_mem(ADDR_HP5883, 0x01, 6)
            mx = parse_s16(d_mag[1], d_mag[0])
            my = parse_s16(d_mag[3], d_mag[2])
            head = math.degrees(math.atan2(my, mx))
            if head < 0: head += 360.0
        except:
            pass

    # 5. Batarya & Akım Monitörü (INA219: 0x40)
    v_bus, i_ma, p_mw = 0.0, 0.0, 0.0
    if i2c:
        try:
            d_v = i2c.readfrom_mem(ADDR_INA219, 0x02, 2)
            v_bus = ((d_v[0] << 8 | d_v[1]) >> 3) * 0.004
            d_s = i2c.readfrom_mem(ADDR_INA219, 0x01, 2)
            s_val = parse_s16(d_s[0], d_s[1])
            i_ma = (s_val * 0.01) / 0.1
            p_mw = v_bus * i_ma
        except:
            pass

    # 6. MicroSD Karta Güvenli Kayıt (5 pakette bir diske mühürle)
    if sd_available and sd_file:
        try:
            log_line = f"{packet_counter},{t_stamp},{alt_m:.2f},{press_hpa:.2f},{temp_c:.2f},{ax:.2f},{ay:.2f},{az:.2f},{gx:.1f},{gy:.1f},{gz:.1f},{head:.1f},{v_bus:.2f},{i_ma:.1f},{p_mw:.1f}\n"
            sd_file.write(log_line)
            if packet_counter % 5 == 0:
                sd_file.flush()
        except:
            pass

    # 7. LoRa Downlink Telemetri Paketi
    if lora:
        telemetry_pkt = (
            f"SFNODE,{packet_counter},{t_stamp},{packet_counter},{temp_c:.1f},{press_hpa:.1f},{alt_m:.1f},"
            f"{ax:.2f},{ay:.2f},{az:.2f},{gx:.0f},{gy:.0f},{gz:.0f},{head:.1f},{v_bus:.2f},{i_ma:.1f}"
        )
        try:
            lora.send(telemetry_pkt)
        except:
            pass

        # 8. Uplink Dinleme Penceresi (150 ms)
        lora.set_rx_mode()
        t_listen = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t_listen) < 150:
            pkt = lora.receive()
            if pkt:
                try:
                    msg = pkt.strip()
                    if msg == f"{CALLSIGN}:PING":
                        time.sleep_ms(20)
                        lora.send(f"{CALLSIGN}:PONG")
                        lora.set_rx_mode()
                    elif msg == f"{CALLSIGN}:SET_MODE:SAFE":
                        time.sleep_ms(20)
                        lora.send(f"{CALLSIGN}:MODE:SAFE:OK")
                        lora.set_rx_mode()
                except:
                    pass
            time.sleep_ms(10)

    led.value(0)
    gc.collect()

    # 1 Hz Frekans Senkronizasyonu
    elapsed = time.ticks_diff(time.ticks_ms(), t_start)
    if elapsed < 1000:
        time.sleep_ms(1000 - elapsed)