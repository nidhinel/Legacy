import tkinter as tk
from tkinter import ttk
import threading
import time
from temperature_sensor import (
    MockTemperatureSensorAPI,
    TemperatureSensorAPI,
    TemperatureReading,
    celsius_to_fahrenheit,
    to_celsius,
)
from config import DEMO_MODE, API_BASE_URL, API_KEY, SENSOR_ID, POLL_INTERVAL


class TemperatureDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Temperature Sensor Dashboard")
        self.geometry("500x520")
        self.minsize(400, 460)
        self.configure(bg="#1e1e2e")

        self.client = MockTemperatureSensorAPI() if DEMO_MODE else TemperatureSensorAPI(API_BASE_URL, API_KEY)
        self.monitoring = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

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

        self.temp_c_label = tk.Label(temp_frame, textvariable=self.temp_c_var,
                                     font=("Helvetica", 52, "bold"), fg="#89b4fa", bg="#1e1e2e")
        self.temp_c_label.pack()
        self.temp_f_label = tk.Label(temp_frame, textvariable=self.temp_f_var,
                                     font=("Helvetica", 22), fg="#74c7ec", bg="#1e1e2e")
        self.temp_f_label.pack()
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

        log_header = tk.Frame(log_frame, bg="#181825")
        log_header.pack(fill="x")
        tk.Label(log_header, text="Reading History", font=("Helvetica", 10, "bold"),
                 fg="#cdd6f4", bg="#181825").pack(side="left")
        tk.Button(log_header, text="Clear", font=("Helvetica", 8),
                  bg="#313244", fg="#a6adc8", relief="flat", cursor="hand2",
                  command=self._clear_log).pack(side="right")

        text_frame = tk.Frame(log_frame, bg="#181825")
        text_frame.pack(fill="both", expand=True, pady=(4, 0))

        self.log_box = tk.Text(text_frame, height=8, bg="#181825", fg="#cdd6f4",
                               font=("Courier", 10), relief="flat",
                               state="disabled", wrap="none")
        self.log_box.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(text_frame, command=self.log_box.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_box.configure(yscrollcommand=scrollbar.set)

    def start_monitoring(self):
        self.monitoring = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self._set_status("Monitoring...", "#a6e3a1")
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def stop_monitoring(self):
        self.monitoring = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self._set_status("Stopped", "#f38ba8")

    def _poll_loop(self):
        while self.monitoring:
            try:
                reading = self.client.get_reading(SENSOR_ID)
                self.after(0, self._update_display, reading)
            except Exception as e:
                self.after(0, self._set_status, f"Error: {e}", "#f38ba8")
            time.sleep(POLL_INTERVAL)

    def _temp_color(self, temp_c: float) -> str:
        if temp_c < 18:
            return "#74c7ec"   # cool — blue
        elif temp_c < 26:
            return "#a6e3a1"   # normal — green
        elif temp_c < 35:
            return "#fab387"   # warm — orange
        return "#f38ba8"       # hot — red

    def _update_display(self, reading: TemperatureReading):
        temp_c = to_celsius(reading)
        temp_f = celsius_to_fahrenheit(temp_c)
        color = self._temp_color(temp_c)

        self.temp_c_var.set(f"{temp_c:.1f}°C")
        self.temp_f_var.set(f"{temp_f:.1f}°F")
        self.location_var.set(f"Location: {reading.location or '—'}")
        self.time_var.set(f"Last update: {reading.timestamp.strftime('%H:%M:%S')}")
        self.temp_c_label.config(fg=color)
        self.temp_f_label.config(fg=color)

        entry = f"[{reading.timestamp.strftime('%H:%M:%S')}]  {temp_c:.2f}°C  /  {temp_f:.2f}°F\n"
        self.log_box.config(state="normal")
        self.log_box.insert("end", entry)
        if int(self.log_box.index("end-1c").split(".")[0]) > 200:
            self.log_box.delete("1.0", "2.0")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

    def _on_close(self):
        self.monitoring = False
        self.client.close()
        self.destroy()

    def _set_status(self, text, color="#a6adc8"):
        self.status_dot.config(fg=color)
        self.status_label.config(text=text, fg=color)


if __name__ == "__main__":
    app = TemperatureDashboard()
    app.mainloop()
