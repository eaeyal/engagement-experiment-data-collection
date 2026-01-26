import time
import tkinter as tk
from tkinter import ttk
from collections import deque
from pylsl import ContinuousResolver, StreamInlet

# ==========================================
# SETTINGS
# ==========================================
WINDOW_DURATION = 10.0   # Window size for "Effective Hz" (Current calculating speed)
REFRESH_RATE_MS = 100    # How often the GUI updates (10fps)

class StreamContainer:
    """Holds data and logic for a single LSL stream."""
    def __init__(self, info):
        self.info = info
        self.name = info.name()
        self.type = info.type()
        self.source_id = info.source_id()
        self.nominal_srate = info.nominal_srate()
        self.channel_count = info.channel_count()
        
        # Unique ID for the GUI table
        self.uid = self.source_id if self.source_id else f"{self.name}_{self.type}"
        
        self.inlet = StreamInlet(info)
        
        # --- Metrics ---
        self.timestamps = deque()       # For sliding window calc
        self.start_time = None          # Time of first sample received
        self.total_samples = 0          # Total samples since connection
        
        self.effective_rate = 0.0       # Last 10s
        self.running_rate = 0.0         # Since start

    def process(self):
        """Pulls data and updates rate calculations."""
        try:
            # Non-blocking pull of all available data
            _, ts = self.inlet.pull_chunk(timeout=0.0)
            
            if ts:
                # Initialize start time if this is the first chunk
                if self.start_time is None:
                    self.start_time = ts[0]

                # Update Counters
                count = len(ts)
                self.total_samples += count
                self.timestamps.extend(ts)
                
                # --- Calc 1: Running Average (Since start) ---
                # Total Samples / (Latest Timestamp - First Timestamp)
                total_duration = ts[-1] - self.start_time
                if total_duration > 1.0: # Avoid noise in first second
                    self.running_rate = self.total_samples / total_duration

            # --- Calc 2: Effective Rate (Sliding Window) ---
            # Prune old timestamps
            if self.timestamps:
                latest = self.timestamps[-1]
                limit = latest - WINDOW_DURATION
                while self.timestamps and self.timestamps[0] < limit:
                    self.timestamps.popleft()

                # Calculate based on what remains in the deque
                if len(self.timestamps) > 1:
                    window_duration = self.timestamps[-1] - self.timestamps[0]
                    if window_duration > 0:
                        self.effective_rate = len(self.timestamps) / window_duration
                else:
                    self.effective_rate = 0.0
            else:
                self.effective_rate = 0.0

        except Exception:
            self.effective_rate = 0.0

class LSLMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LSL Stream Monitor")
        self.root.geometry("950x450")

        # 1. Background Resolver (Continuously looks for streams)
        self.resolver = ContinuousResolver()
        self.streams = {} # Map uid -> StreamContainer

        # 2. GUI Setup
        self.setup_ui()

        # 3. Start Loops
        self.running = True
        self.update_streams_loop()
        self.update_gui_loop()

    def setup_ui(self):
        # Styling
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", rowheight=30, font=('Segoe UI', 10))
        style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))

        # Define Columns
        columns = ("name", "type", "chans", "nominal", "effective", "running", "status")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings")
        
        # Configure Headers
        self.tree.heading("name", text="Stream Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("chans", text="Ch")
        self.tree.heading("nominal", text="Nominal Hz")
        self.tree.heading("effective", text="Effective Hz (10s)")
        self.tree.heading("running", text="Running Avg Hz")
        self.tree.heading("status", text="Status")

        # Configure Columns
        self.tree.column("name", width=220)
        self.tree.column("type", width=120)
        self.tree.column("chans", width=50, anchor="center")
        self.tree.column("nominal", width=100, anchor="center")
        self.tree.column("effective", width=130, anchor="center")
        self.tree.column("running", width=130, anchor="center")
        self.tree.column("status", width=150, anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        # Layout
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Row Colors
        self.tree.tag_configure("ok", background="#e6fffa")     # Greenish
        self.tree.tag_configure("warn", background="#fffacd")   # Yellowish
        self.tree.tag_configure("error", background="#ffe6e6")  # Reddish

    def update_streams_loop(self):
        """Checks for new streams every 500ms."""
        if not self.running: return

        results = self.resolver.results()
        
        for info in results:
            uid = info.source_id() if info.source_id() else f"{info.name()}_{info.type()}"

            # Register new stream
            if uid not in self.streams:
                container = StreamContainer(info)
                self.streams[uid] = container
                # Insert empty row
                self.tree.insert("", "end", iid=uid, values=(
                    container.name, container.type, container.channel_count, 
                    container.nominal_srate, "0.0", "0.0", "Init..."
                ))
        
        # Process data logic
        for container in self.streams.values():
            container.process()

        self.root.after(50, self.update_streams_loop)

    def update_gui_loop(self):
        """Refreshes the GUI table values."""
        if not self.running: return

        for uid, s in self.streams.items():
            # Status Logic
            status_text = "OK"
            tag = "ok"
            
            # Calculate deviation based on "Effective" (Current) rate
            diff = 0
            if s.nominal_srate > 0:
                diff = abs(s.effective_rate - s.nominal_srate) / s.nominal_srate

            if s.effective_rate == 0:
                status_text = "NO DATA"
                tag = "error"
            elif diff > 0.15: # >15% deviation
                status_text = "UNSTABLE"
                tag = "warn"
            
            # Format numbers
            eff_str = f"{s.effective_rate:.1f}"
            run_str = f"{s.running_rate:.2f}"
            
            # Update Treeview Row
            try:
                self.tree.item(uid, values=(
                    s.name, 
                    s.type, 
                    s.channel_count, 
                    s.nominal_srate, 
                    eff_str,
                    run_str,
                    status_text
                ), tags=(tag,))
            except tk.TclError:
                pass # Row might have been deleted (not implemented here but good safety)

        self.root.after(REFRESH_RATE_MS, self.update_gui_loop)

    def on_close(self):
        self.running = False
        self.root.destroy()

def start_lsl_monitor():
    root = tk.Tk()
    app = LSLMonitorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()