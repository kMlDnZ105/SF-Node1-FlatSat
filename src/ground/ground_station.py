# ===================================================================
# PROJE: S&F Node - Bilgisayar Yer İstasyonu Terminali (Ground Control)
# ÇALIŞTIRMA: python ground_station.py
# ===================================================================
import serial
import serial.tools.list_ports
import threading
import time
import sys

# COM Port Ayarı: Pico'nun bağlı olduğu port (Örn: COM4, COM5)
# Boş bırakırsan otomatik bulmaya çalışır.
TARGET_PORT = "COM5" 
BAUD_RATE = 115200
LOG_FILE = "ground_telemetry.csv"

def find_pico_port():
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if "Board CDC" in p.description or "Pico" in p.description or "Serial" in p.description:
            return p.device
    return None

def parse_telemetry(line):
    # CSV Formatı: SFNODE,ID,TIMESTAMP,UPTIME,TEMP,PRESS,ALT,AX,AY,AZ,GX,GY,GZ,HEAD,VBAT,ICURR
    parts = line.strip().split(",")
    if len(parts) >= 16 and parts[0] == "SFNODE":
        print("\n" + "="*65)
        print(f" [UYDU TELEMETRİSİ] Paket #{parts[1]} | Zaman: {parts[2]} | Uptime: {parts[3]}s")
        print("="*65)
        print(f"  ÇEVRE     : Sıcaklık: {parts[4]}°C | Basınç: {parts[5]} hPa | İrtifa: {parts[6]} m")
        print(f"  YÖNELİM   : Pusula: {parts[13]}° | İvme (Z): {parts[9]}g")
        print(f"  GÜÇ (EPS) : Batarya: {parts[14]}V | Çekilen Akım: {parts[15]} mA")
        print("="*65 + "\nKomut girin (örn: TB2CDF:PING) > ", end="", flush=True)

        # Diske logla
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return True
    return False

def listen_serial(ser):
    while True:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                if not parse_telemetry(line):
                    # Telemetri dışındaki yanıtlar (PONG, ACK, LOG)
                    print(f"\n[RX] {line}\nKomut girin > ", end="", flush=True)
        except Exception:
            break

def main():
    global TARGET_PORT
    port = TARGET_PORT or find_pico_port()
    if not port:
        print("[HATA] Pico COM portu bulunamadı. Lütfen TARGET_PORT değişkenine COM portunu yazın.")
        return

    print(f"[GS] {port} portuna bağlanılıyor ({BAUD_RATE} baud)...")
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=1)
        print(f"[GS] Yer İstasyonu Dinlemede. Log dosyası: {LOG_FILE}\n")
    except Exception as e:
        print(f"[HATA] Porta bağlanılamadı: {e}")
        return

    # Arka planda gelen telsiz paketlerini dinleyen thread
    t = threading.Thread(target=listen_serial, args=(ser,), daemon=True)
    t.start()

    time.sleep(1)
    print("Kullanılabilir Komutlar:")
    print("  TB2CDF:PING")
    print("  TB2CDF:MSG_STORE:<ID>:<MESAJ>")
    print("  TB2CDF:MSG_GET:<ID>")
    print("  TB2CDF:SET_MODE:SAFE\n")

    while True:
        try:
            cmd = input("Komut girin > ")
            if cmd.strip():
                ser.write((cmd + "\n").encode('utf-8'))
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[GS] Kapatılıyor...")
            ser.close()
            sys.exit(0)

if __name__ == "__main__":
    main()