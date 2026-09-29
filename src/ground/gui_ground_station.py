import os
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import serial.tools.list_ports

TARGET_PORT = "COM5"
BAUD_RATE = 115200
DEFAULT_BAT_CAPACITY_MAH = 3000

# Kayıt Dosyası Yolu
current_dir = os.path.dirname(os.path.abspath(__file__))
CSV_LOG_PATH = os.path.join(current_dir, "ground_telemetry.csv")

def get_battery_soc(voltage):
    """1S Li-Po Gerilim - Doluluk Yüzdesi (%) Eğrisi"""
    lut = [
        (4.20, 100.0), (4.10, 90.0), (4.00, 78.0), (3.90, 62.0),
        (3.83, 50.0), (3.78, 38.0), (3.72, 22.0), (3.65, 12.0),
        (3.55, 5.0), (3.30, 0.0)
    ]
    if voltage >= 4.20: return 100.0
    if voltage <= 3.30: return 0.0
    for i in range(len(lut) - 1):
        v_high, soc_high = lut[i]
        v_low, soc_low = lut[i + 1]
        if v_low <= voltage <= v_high:
            return soc_low + (voltage - v_low) * (soc_high - soc_low) / (v_high - v_low)
    return 0.0

class GroundStationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TB2CDF - Aviyonik Yer İstasyonu (24S Saha Testi)")
        self.root.geometry("1080x720")
        self.root.configure(bg="#1e1e1e")

        # CSV Kayıt Dosyasını Başlat
        self.init_csv_log()

        # ======================================================================
        # 1. ÜST PANEL: BÜYÜK GÖSTERGELER (3x2 GRID)
        # ======================================================================
        frame_telemetry = tk.LabelFrame(root, text=" Canlı Aviyonik & Enerji Durumu ", bg="#1e1e1e", fg="#00ffcc", font=("Consolas", 11, "bold"))
        frame_telemetry.pack(fill="x", padx=10, pady=5)

        self.lbl_alt = tk.Label(frame_telemetry, text="İRTİFA: -- m", font=("Consolas", 13, "bold"), bg="#1e1e1e", fg="#ffffff")
        self.lbl_alt.grid(row=0, column=0, padx=15, pady=6, sticky="w")

        self.lbl_temp = tk.Label(frame_telemetry, text="SICAKLIK: -- °C", font=("Consolas", 13, "bold"), bg="#1e1e1e", fg="#ff5555")
        self.lbl_temp.grid(row=0, column=1, padx=15, pady=6, sticky="w")

        self.lbl_bat = tk.Label(frame_telemetry, text="GERİLİM: -- V", font=("Consolas", 13, "bold"), bg="#1e1e1e", fg="#00ff00")
        self.lbl_bat.grid(row=0, column=2, padx=15, pady=6, sticky="w")

        self.lbl_soc = tk.Label(frame_telemetry, text="DOLULUK: %--", font=("Consolas", 13, "bold"), bg="#1e1e1e", fg="#33ccff")
        self.lbl_soc.grid(row=1, column=0, padx=15, pady=6, sticky="w")

        self.lbl_cur = tk.Label(frame_telemetry, text="AKIM: -- mA", font=("Consolas", 13, "bold"), bg="#1e1e1e", fg="#ffcc00")
        self.lbl_cur.grid(row=1, column=1, padx=15, pady=6, sticky="w")

        self.lbl_time_left = tk.Label(frame_telemetry, text="KALAN SÜRE: -- sa -- dk", font=("Consolas", 13, "bold"), bg="#1e1e1e", fg="#ff9933")
        self.lbl_time_left.grid(row=1, column=2, padx=15, pady=6, sticky="w")

        # ======================================================================
        # 2. ORTA PANEL: UPLINK MERKEZİ & PİL AYARI
        # ======================================================================
        frame_cmds = tk.LabelFrame(root, text=" Uplink Komut Merkezi ", bg="#1e1e1e", fg="#00ffcc", font=("Consolas", 11, "bold"))
        frame_cmds.pack(fill="x", padx=10, pady=5)

        btn_ping = tk.Button(frame_cmds, text="⚡ TB2CDF:PING", bg="#0055ff", fg="white", font=("Consolas", 10, "bold"), command=lambda: self.send_command("TB2CDF:PING"))
        btn_ping.pack(side="left", padx=8, pady=5)

        btn_safe = tk.Button(frame_cmds, text="🛡️ SAFE MODE", bg="#aa0000", fg="white", font=("Consolas", 10, "bold"), command=lambda: self.send_command("TB2CDF:SET_MODE:SAFE"))
        btn_safe.pack(side="left", padx=8, pady=5)

        tk.Label(frame_cmds, text="Pil Kapasitesi (mAh):", bg="#1e1e1e", fg="#ffffff", font=("Consolas", 10)).pack(side="left", padx=(20, 2))
        self.entry_cap = tk.Entry(frame_cmds, width=6, font=("Consolas", 10), bg="#2d2d2d", fg="#ffffff")
        self.entry_cap.insert(0, str(DEFAULT_BAT_CAPACITY_MAH))
        self.entry_cap.pack(side="left", padx=2)

        frame_input = tk.Frame(root, bg="#1e1e1e")
        frame_input.pack(fill="x", padx=10, pady=5)

        self.entry_cmd = tk.Entry(frame_input, font=("Consolas", 11), bg="#2d2d2d", fg="#ffffff", insertbackground="white")
        self.entry_cmd.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_cmd.bind("<Return>", lambda event: self.send_custom())

        btn_send = tk.Button(frame_input, text="GÖNDER", bg="#28a745", fg="white", font=("Consolas", 10, "bold"), command=self.send_custom)
        btn_send.pack(side="right")

        # ======================================================================
        # 3. ALT PANEL: SENSÖR AKIŞ TERMİNALİ
        # ======================================================================
        header_text = " SAAT     PKT  | SICAK   BASINÇ    İRTİFA  | İVME (X,Y,Z)[g]        | JİRO (X,Y,Z)[°/s]       | PUSULA | GÜÇ DURUMU"
        lbl_head = tk.Label(root, text=header_text, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", anchor="w")
        lbl_head.pack(fill="x", padx=10, pady=(4, 0))

        self.txt_log = scrolledtext.ScrolledText(root, bg="#0d0d0d", fg="#00ff66", font=("Consolas", 9), insertbackground="white", wrap="none")
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        self.ser = None
        self.connect_serial()

    def init_csv_log(self):
        file_exists = os.path.exists(CSV_LOG_PATH)
        self.log_file = open(CSV_LOG_PATH, "a", encoding="utf-8")
        if not file_exists:
            # Standart yer telemetrisi başlığı
            self.log_file.write("HEADER,PKT_ID,UTC_TIME,UPTIME,TEMP,PRESS,ALT,AX,AY,AZ,GX,GY,GZ,HEAD,VBAT,ICURR\n")
            self.log_file.flush()

    def connect_serial(self):
        try:
            self.ser = serial.Serial(TARGET_PORT, BAUD_RATE, timeout=0.1)
            self.log(f"[SİSTEM] {TARGET_PORT} portuna bağlanıldı. Kayıt: ground_telemetry.csv")
            t = threading.Thread(target=self.read_serial, daemon=True)
            t.start()
        except Exception as e:
            self.log(f"[HATA] Porta bağlanılamadı: {e}")

    def read_serial(self):
        while self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    self.root.after(0, self.process_line, line)
            except:
                break

    def process_line(self, line):
        # 1. Dosyaya diske zorlayarak kaydet
        if line.startswith("SFNODE"):
            try:
                self.log_file.write(line + "\n")
                self.log_file.flush()
            except:
                pass

        parts = line.split(",")
        if len(parts) >= 16 and parts[0] == "SFNODE":
            try:
                pkt_id = parts[1]
                t_stamp = parts[2]
                temp = float(parts[4])
                press = float(parts[5])
                alt = float(parts[6])
                ax, ay, az = float(parts[7]), float(parts[8]), float(parts[9])
                gx, gy, gz = float(parts[10]), float(parts[11]), float(parts[12])
                head = float(parts[13])
                vbat = float(parts[14])
                icur = float(parts[15])

                # Pil Hesabı
                soc = get_battery_soc(vbat)
                try: cap = float(self.entry_cap.get())
                except: cap = DEFAULT_BAT_CAPACITY_MAH

                rem_mah = cap * (soc / 100.0)
                if icur > 0.5:
                    hours_total = rem_mah / icur
                    hrs = int(hours_total)
                    mins = int((hours_total - hrs) * 60)
                    time_str = f"{hrs} sa {mins:02d} dk"
                else:
                    time_str = "Hesaplanıyor..."

                # Üst Göstergeler
                self.lbl_alt.config(text=f"İRTİFA: {alt:.1f} m")
                self.lbl_temp.config(text=f"SICAKLIK: {temp:.1f} °C")
                self.lbl_bat.config(text=f"GERİLİM: {vbat:.2f} V")
                self.lbl_soc.config(text=f"DOLULUK: %{soc:.0f}")
                self.lbl_cur.config(text=f"AKIM: {icur:.1f} mA")
                self.lbl_time_left.config(text=f"KALAN SÜRE: {time_str}")

                # Terminal Akışı
                time_only = t_stamp.split(" ")[-1] if " " in t_stamp else t_stamp
                full_stream_line = (
                    f"{time_only} #{pkt_id:<5} | "
                    f"{temp:4.1f}°C {press:6.1f}hPa {alt:6.1f}m | "
                    f"A:[{ax:+4.2f},{ay:+4.2f},{az:+4.2f}]g | "
                    f"G:[{gx:+4.0f},{gy:+4.0f},{gz:+4.0f}]°/s | "
                    f"{head:5.1f}° | "
                    f"{vbat:4.2f}V {icur:4.1f}mA (%{soc:.0f} - {time_str})"
                )
                self.log(full_stream_line)
            except Exception:
                pass
        else:
            self.log(f">> {line}")

    def send_command(self, cmd):
        if self.ser and self.ser.is_open:
            self.ser.write((cmd + "\n").encode('utf-8'))
            self.log(f"[UPLINK GÖNDERİLDİ] -> {cmd}")

    def send_custom(self):
        cmd = self.entry_cmd.get().strip()
        if cmd:
            self.send_command(cmd)
            self.entry_cmd.delete(0, tk.END)

    def log(self, msg):
        self.txt_log.insert(tk.END, f"{msg}\n")
        self.txt_log.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = GroundStationApp(root)
    root.mainloop()