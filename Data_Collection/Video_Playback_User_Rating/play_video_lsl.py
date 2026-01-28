import sys
import time
import vlc
import platform
import tkinter as tk
from pathlib import Path
from pylsl import StreamInfo, StreamOutlet
from pynput import keyboard

# ==========================================
# CONFIGURATION
# ==========================================
# Update these paths to your local files
VIDEO_PATH = Path(__file__).parent / "videos" / "Kurzgezagt_Quantum_Computers.mp4"
BEEP_PATH = Path(__file__).parent / "audio" / "beep.mp3"

# LSL Settings - Stream 1 (Time)
STREAM_NAME_TIME = "Video_Time_Data"
STREAM_TYPE_TIME = "Time_Markers"
STREAM_ID_TIME = "vid_time_stream_001"

# LSL Settings - Stream 2 (Engagement)
STREAM_NAME_ENG = "Engagement_Rating"
STREAM_TYPE_ENG = "Rating"
STREAM_ID_ENG = "vid_rating_stream_001"

# Experiment Settings
PAUSE_INTERVAL_SECONDS = 60

class BehavioralVideoPlayer(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("LSL Engagement Experiment (Dual Stream)")
        self.geometry("1920x1080")
        self.configure(bg="black")
        
        # --- State Variables ---
        self.is_fullscreen = False
        self.last_trigger_second = 0 
        self.waiting_for_input = False 
        self.current_engagement_rating = 0 # Defaults to 0 until first input
        
        # --- 1. Setup LSL (Two Separate Streams) ---
        
        # Stream 1: Video Time (1 channel, Irregular rate set to 0, int32)
        info_time = StreamInfo(STREAM_NAME_TIME, STREAM_TYPE_TIME, 1, 0, 'int32', STREAM_ID_TIME)
        self.outlet_time = StreamOutlet(info_time)
        
        # Stream 2: Engagement (1 channel, Irregular rate set to 0, int32)
        info_eng = StreamInfo(STREAM_NAME_ENG, STREAM_TYPE_ENG, 1, 0, 'int32', STREAM_ID_ENG)
        self.outlet_eng = StreamOutlet(info_eng)
        
        print(f"LSL Streams Created:\n 1. {STREAM_NAME_TIME}\n 2. {STREAM_NAME_ENG}")

        # --- 2. Setup GUI ---
        self.video_frame = tk.Frame(self, bg="black")
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        
        # Overlay Label (Hidden by default)
        self.overlay_label = tk.Label(
            self, 
            text="PAUSED\n\nPress 1-5 to Rate Engagement\nand Resume Video", 
            fg="yellow", bg="black", 
            font=("Arial", 32, "bold")
        )

        self.status_label = tk.Label(self, text="Ready", fg="gray", bg="black", font=("Arial", 14))
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # --- 3. Setup VLC ---
        self.instance = vlc.Instance("--input-repeat=0")
        self.video_player = self.instance.media_player_new()
        self.sfx_player = self.instance.media_player_new()

        if not VIDEO_PATH.exists():
            print(f"ERROR: Video not found: {VIDEO_PATH}")
        else:
            media = self.instance.media_new(str(VIDEO_PATH))
            self.video_player.set_media(media)

        if not BEEP_PATH.exists():
            print(f"WARNING: Beep file not found: {BEEP_PATH}")
        else:
            self.sfx_media = self.instance.media_new(str(BEEP_PATH))

        # Embed VLC
        self.update() 
        handle = self.video_frame.winfo_id()
        system = platform.system()
        if system == "Windows":
            self.video_player.set_hwnd(handle)
        elif system == "Darwin": 
            try: self.video_player.set_nsobject(handle)
            except: pass 
        else: 
            self.video_player.set_xwindow(handle)

        # --- 4. Input Listeners ---
        self.bind("<f>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_fullscreen)
        self.bind("<q>", self.quit_app)
        self.bind("<space>", self.toggle_play)

        # Global Keyboard Listener
        self.listener = keyboard.Listener(on_press=self.on_global_keypress)
        self.listener.start()

        # Start Loop
        self.update_loop()

    def update_loop(self):
        """Main logic loop running at ~30Hz"""
        
        # 1. Get Video Time
        t_ms = self.video_player.get_time()
        seconds = max(0, int(t_ms // 1000))
        
        # 2. Check for 60-Second Trigger
        if (seconds > 0 and 
            seconds % PAUSE_INTERVAL_SECONDS == 0 and 
            seconds != self.last_trigger_second and 
            not self.waiting_for_input):
            
            self.trigger_engagement_check(seconds)

        # 3. LSL Streams (Push Separate Samples)
        # Push current video time
        self.outlet_time.push_sample([seconds])
        
        # Push current rating (Always streams the last held value)
        self.outlet_eng.push_sample([self.current_engagement_rating])
        
        # 4. GUI Update
        if self.waiting_for_input:
             self.status_label.config(text=f"WAITING FOR INPUT (1-5)... Time: {seconds}")
        elif self.video_player.is_playing():
             m, s = divmod(seconds, 60)
             self.status_label.config(text=f"Playing - {m:02d}:{s:02d} | Current Rating: {self.current_engagement_rating}")

        self.after(33, self.update_loop)

    def trigger_engagement_check(self, timestamp):
        """Pauses video, plays beep, blocks until input."""
        print(f"Triggering Check at {timestamp}s")
        
        self.video_player.set_pause(1) 
        
        if BEEP_PATH.exists():
            self.sfx_player.set_media(self.sfx_media) 
            self.sfx_player.play()
        
        self.waiting_for_input = True
        self.last_trigger_second = timestamp
        
        self.overlay_label.place(relx=0.5, rely=0.5, anchor="center")

    def on_global_keypress(self, key):
        """Handles pynput events."""
        # STRICT RULE: Ignore input if we are NOT waiting for a rating
        if not self.waiting_for_input:
            return

        try:
            if hasattr(key, 'char') and key.char in '12345':
                val = int(key.char)
                
                # Update the rating only now
                self.current_engagement_rating = val
                print(f"Rating updated to: {val}")

                # Unlock and resume
                self.resume_video()
                    
        except AttributeError:
            pass

    def resume_video(self):
        """Resumes playback after input received."""
        print("Resuming video...")
        self.waiting_for_input = False
        self.overlay_label.place_forget() 
        self.video_player.set_pause(0)    

    def toggle_play(self, event=None):
        # Disable manual toggle during engagement check
        if self.waiting_for_input:
            return 
            
        if self.video_player.is_playing():
            self.video_player.pause()
        else:
            self.video_player.play()

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)

    def exit_fullscreen(self, event=None):
        self.is_fullscreen = False
        self.attributes("-fullscreen", False)

    def quit_app(self, event=None):
        self.listener.stop()
        self.video_player.stop()
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    app = BehavioralVideoPlayer()
    app.mainloop()