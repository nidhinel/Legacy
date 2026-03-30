import tkinter as tk
from tkinter import ttk
import threading
import time
from datetime import datetime
from temperature_sensor import MockTemperatureSensorAPI, TemperatureSensorAPI

# --- Configuration ---
DEMO_MODE = True
API_BASE_URL = "https://api.example.com/v1"
API_KEY = "your_api_key_here"
SENSOR_ID = "sensor_001"
POLL_INTERVAL = 2  # seconds


class TemperatureDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Temperature Sensor Dashboard")
        self.geometry("500x520")
        self.resizable(False, False)
        self.configure(bg="#1e1e2e")

        self.client = MockTemperatureSensorAPI() if DEMO_MODE else TemperatureSensorAPI(API_BASE_URL, API_KEY)
        self.monitoring = False
        self.readings = []

        self._build_ui()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg="#313244", pady=12)
        header.pack(fill="x")
        tk.Label(header, text="Temperature Sensor Dashboard",
                 font=("Helvetica", 16, "bold"), fg="#cdd6f4", bg="#313244").pack()
        mode = "DEMO MODE" if DEMO_MODE else "LIVE"
        tk.Label(header, text=f"Sensor: {SENSOR_ID}  |  {mode}",
                 font=("Helvetica", 9), fg="#a6adc8", bg="#313244").pack()

        # Temperature display
        temp_frame = tk.Frame(self, bg="#1e1e2e", pady=20)
        temp_frame.pack(fill="x")

        self.temp_c_var = tk.StringVar(value="--.-°C")
        self.temp_f_var = tk.StringVar(value="--.-°F")
        self.location_var = tk.StringVar(value="Location: —")
        self.time_var = tk.StringVar(value="Last update: —")

        tk.Label(temp_frame, textvariable=self.temp_c_var,
                 font=("Helvetica", 52, "bold"), fg="#89b4fa", bg="#1e1e2e").pack()
        tk.Label(temp_frame, textvariable=self.temp_f_var,
                 font=("Helvetica", 22), fg="#74c7ec", bg="#1e1e2e").pack()
        tk.Label(temp_frame, textvariable=self.location_var,
                 font=("Helvetica", 10), fg="#a6adc8", bg="#1e1e2e").pack(pady=(6, 0))
        tk.Label(temp_frame, textvariable=self.time_var,
                 font=("Helvetica", 9), fg="#6c7086", bg="#1e1e2e").pack()

        # Status indicator
        status_frame = tk.Frame(self, bg="#1e1e2e")
        status_frame.pack()
        self.status_dot = tk.Label(status_frame, text="●", font=("Helvetica", 12),
                                   fg="#6c7086", bg="#1e1e2e")
        self.status_dot.pack(side="left")
        self.status_label = tk.Label(status_frame, text="Idle", font=("Helvetica", 10),
                                     fg="#6c7086", bg="#1e1e2e")
        self.status_label.pack(side="left", padx=4)

        # Controls
        btn_frame = tk.Frame(self, bg="#1e1e2e", pady=14)
        btn_frame.pack()
        self.start_btn = tk.Button(btn_frame, text="Start Monitoring", width=16,
                                   font=("Helvetica", 11, "bold"),
                                   bg="#a6e3a1", fg="#1e1e2e", relief="flat",
                                   cursor="hand2", command=self.start_monitoring)
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = tk.Button(btn_frame, text="Stop", width=10,
                                  font=("Helvetica", 11),
                                  bg="#f38ba8", fg="#1e1e2e", relief="flat",
                                  cursor="hand2", command=self.stop_monitoring,
                                  state="disabled")
        self.stop_btn.pack(side="left", padx=6)

        # History log
        log_frame = tk.Frame(self, bg="#181825", pady=10, padx=10)
        log_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        tk.Label(log_frame, text="Reading History", font=("Helvetica", 10, "bold"),
                 fg="#cdd6f4", bg="#181825").pack(anchor="w")

        self.log_box = tk.Text(log_frame, height=8, bg="#181825", fg="#cdd6f4",
                               font=("Courier", 10), relief="flat",
                               state="disabled", wrap="none")
        self.log_box.pack(fill="both", expand=True, pady=(4, 0))

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=scrollbar.set)

    def start_monitoring(self):
        self.monitoring = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self._set_status("Monitoring...", "#a6e3a1")
        thread = threading.Thread(target=self._poll_loop, daemon=True)
        thread.start()

    def stop_monitoring(self):
        self.monitoring = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self._set_status("Stopped", "#f38ba8")

    def _poll_loop(self):
        while self.monitoring:
            try:
                reading = self.client.get_reading(SENSOR_ID)
                temp_f = (reading.temperature * 9 / 5) + 32
                self.after(0, self._update_display, reading.temperature, temp_f,
                           reading.location, reading.timestamp)
            except Exception as e:
                self.after(0, self._set_status, f"Error: {e}", "#f38ba8")
            time.sleep(POLL_INTERVAL)

    def _update_display(self, temp_c, temp_f, location, timestamp):
        self.temp_c_var.set(f"{temp_c:.1f}°C")
        self.temp_f_var.set(f"{temp_f:.1f}°F")
        self.location_var.set(f"Location: {location or '—'}")
        self.time_var.set(f"Last update: {timestamp.strftime('%H:%M:%S')}")
        self._set_status("Monitoring...", "#a6e3a1")

        # Append to log (cap at 200 entries)
        entry = f"[{timestamp.strftime('%H:%M:%S')}]  {temp_c:.2f}°C  /  {temp_f:.2f}°F\n"
        self.log_box.config(state="normal")
        self.log_box.insert("end", entry)
        if int(self.log_box.index("end-1c").split(".")[0]) > 200:
            self.log_box.delete("1.0", "2.0")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _set_status(self, text, color="#a6adc8"):
        self.status_dot.config(fg=color)
        self.status_label.config(text=text, fg=color)


if __name__ == "__main__":
    app = TemperatureDashboard()
    app.mainloop()
