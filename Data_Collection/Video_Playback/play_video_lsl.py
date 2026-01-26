import sys
import time
import vlc
import platform
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from pylsl import StreamInfo, StreamOutlet

# ==========================================
# CONFIGURATION
# ==========================================
# Replace with your specific path
VIDEO_PATH = Path(__file__).parent / "videos" / "Kurzgezagt_Quantum_Computers.mp4"

# LSL Settings
STREAM_NAME = "Video_Seconds"
STREAM_TYPE = "Markers"
STREAM_ID = "vid_timer_int_1080"

class VLCPlayerLSL(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("LSL Video Player (1080p)")
        # Change resolution to 1080p
        self.geometry("1920x1080")
        self.configure(bg="black")
        
        # Initialize State
        self.is_fullscreen = False
        self.is_playing = False
        
        # 1. Setup LSL (Modified for Integers)
        # Channel count = 1, Rate = 0 (irregular), Format = int32
        info = StreamInfo(STREAM_NAME, STREAM_TYPE, 1, 0, 'int32', STREAM_ID)
        self.outlet = StreamOutlet(info)
        print(f"LSL Stream '{STREAM_NAME}' created (Format: Integer Seconds).")

        # 2. Setup GUI Elements
        self.video_frame = tk.Frame(self, bg="black")
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_label = tk.Label(self, text="Paused", fg="white", bg="black", font=("Arial", 16))
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # 3. Setup VLC
        self.instance = vlc.Instance("--input-repeat=0")
        self.player = self.instance.media_player_new()
        
        if not VIDEO_PATH.exists():
            print(f"ERROR: File not found: {VIDEO_PATH}")
            # We don't destroy immediately so user sees the error
        else:
            media = self.instance.media_new(str(VIDEO_PATH))
            self.player.set_media(media)

        # 4. Embed VLC into Tkinter
        self.update() # Force update to get valid ID
        handle = self.video_frame.winfo_id()
        
        system = platform.system()
        if system == "Windows":
            self.player.set_hwnd(handle)
        elif system == "Darwin": 
            try: self.player.set_nsobject(handle)
            except: pass 
        else: 
            self.player.set_xwindow(handle)

        # 5. Bindings
        self.bind("<space>", self.toggle_play)
        self.bind("<f>", self.toggle_fullscreen)
        self.bind("<F>", self.toggle_fullscreen)
        self.bind("<r>", self.reset_video)
        self.bind("<q>", self.quit_app)
        self.bind("<Escape>", self.exit_fullscreen)

        # Start LSL Loop
        self.update_lsl()

    def update_lsl(self):
        """Runs periodically to push LSL timestamps as Integers."""
        # Get time in milliseconds
        t_ms = self.player.get_time()
        
        # Convert to seconds (integer)
        if t_ms < 0:
            seconds = 0
        else:
            seconds = int(t_ms // 1000)
            
        # Push Integer to LSL
        self.outlet.push_sample([seconds])
        
        # Update Status Label (Optional visual check)
        if self.player.is_playing():
             # Just showing MM:SS for user benefit, but streaming raw seconds
             m, s = divmod(seconds, 60)
             self.status_label.config(text=f"Playing - {m:02d}:{s:02d} (LSL: {seconds})")

        # Re-schedule (30 Hz)
        self.after(33, self.update_lsl)

    def toggle_play(self, event=None):
        if self.player.is_playing():
            self.player.pause()
            self.status_label.config(text="Paused")
        else:
            self.player.play()

    def reset_video(self, event=None):
        self.player.stop()
        self.player.play()
        self.after(100, lambda: self.player.set_pause(1))
        self.status_label.config(text="Reset to Start")

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        if not self.is_fullscreen:
            self.geometry("1920x1080")

    def exit_fullscreen(self, event=None):
        self.is_fullscreen = False
        self.attributes("-fullscreen", False)
        self.geometry("1920x1080")

    def quit_app(self, event=None):
        self.player.stop()
        self.destroy()

def start_video_playback_lsl():
    app = VLCPlayerLSL()
    app.mainloop()