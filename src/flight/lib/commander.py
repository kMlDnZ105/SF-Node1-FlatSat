# S&F Node - Telekomut (TC) Ayrıştırıcı ve RAM Mailbox Motoru
import time

class CommandHandler:
    def __init__(self, callsign="TB2CDF"):
        self.callsign = callsign
        self.flight_mode = "NOMINAL"  # NOMINAL, SAFE_MODE, BEACON_ONLY
        self.mailbox = {}  # {msg_id: {"sender": ..., "body": ..., "ts": ...}}
        self.telemetry_interval = 5   # Saniye cinsinden

    def parse_packet(self, raw_packet):
        """
        Paket Formatı: CALLSIGN:KOMUT:PARAMETRE1:PARAMETRE2
        Örnekler:
          TB2CDF:PING
          TB2CDF:GET_MODE
          TB2CDF:SET_MODE:SAFE
          TB2CDF:MSG_STORE:ANKARA01:Selam Dunya
          TB2CDF:MSG_GET:ANKARA01
          TB2CDF:MSG_LIST
        """
        if not raw_packet or not isinstance(raw_packet, str):
            return "ERR:INVALID_INPUT"

        parts = raw_packet.strip().split(":")
        
        # 1. Çağrı İşareti (Callsign) Filtresi
        if len(parts) < 2 or parts[0] != self.callsign:
            return f"ERR:CALLSIGN_REJECTED (Beklenen: {self.callsign})"

        cmd = parts[1].upper()
        args = parts[2:]

        # 2. Komut Yönlendirme (Command Dispatcher)
        if cmd == "PING":
            return f"{self.callsign}:PONG:ACK"

        elif cmd == "GET_MODE":
            uptime = time.ticks_ms() // 1000
            return f"{self.callsign}:MODE:{self.flight_mode}:UPTIME:{uptime}s:INTERVAL:{self.telemetry_interval}s"

        elif cmd == "SET_MODE":
            if not args:
                return "ERR:MISSING_MODE_ARG"
            new_mode = args[0].upper()
            if new_mode in ("NOMINAL", "SAFE"):
                self.flight_mode = new_mode
                self.telemetry_interval = 5 if new_mode == "NOMINAL" else 60
                return f"{self.callsign}:MODE_UPDATED:{self.flight_mode}:INTERVAL:{self.telemetry_interval}s"
            return "ERR:UNKNOWN_MODE"

        # --- STORE (Mesaj Saklama) ---
        elif cmd == "MSG_STORE":
            if len(args) < 2:
                return "ERR:USAGE:MSG_STORE:<ID>:<METIN>"
            msg_id = args[0]
            body = ":".join(args[1:])  # Metin içinde iki nokta varsa koru
            self.mailbox[msg_id] = {
                "body": body,
                "timestamp": time.ticks_ms() // 1000
            }
            return f"{self.callsign}:STORE_OK:ID={msg_id}:TOTAL={len(self.mailbox)}"

        # --- FORWARD (Mesaj Okuma / Yere İndirme) ---
        elif cmd == "MSG_GET":
            if not args:
                return "ERR:MISSING_MSG_ID"
            msg_id = args[0]
            if msg_id in self.mailbox:
                data = self.mailbox[msg_id]
                return f"{self.callsign}:MSG_DATA:{msg_id}:{data['body']}"
            return f"ERR:MSG_NOT_FOUND:{msg_id}"

        elif cmd == "MSG_LIST":
            keys = ",".join(self.mailbox.keys()) if self.mailbox else "EMPTY"
            return f"{self.callsign}:MSG_LIST:{keys}"

        else:
            return f"ERR:UNKNOWN_CMD:{cmd}"