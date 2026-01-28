import vlc
import time
import sys
from pathlib import Path
from pylsl import StreamInfo, StreamOutlet
from pynput import keyboard

# ==========================================
# CONFIGURATION
# ==========================================
VIDEO_PATH = Path(__file__).parent / "videos" / "Kurzgezagt_Quantum_Computers.mp4"
BEEP_PATH = Path(__file__).parent / "audio" / "beep.mp3"

PAUSE_INTERVAL = 60  # Seconds

# ==========================================
# GLOBAL STATE
# ==========================================
current_rating = 0       
waiting_for_input = False 
input_received = False   
player = None            # Will hold the VLC player instance

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def on_press(key):
    global current_rating, waiting_for_input, input_received, player
    
    # 1. HANDLE ENGAGEMENT INPUT (Blocking Mode)
    if waiting_for_input:
        try:
            if hasattr(key, 'char') and key.char in '12345':
                new_val = int(key.char)
                current_rating = new_val
                print(f"\n[INPUT] User Rated: {new_val}")
                input_received = True # Unlocks the main loop
        except AttributeError:
            pass
        return # Ignore other keys (like space) while waiting for rating

    # 2. HANDLE SPACEBAR (Normal Mode)
    if key == keyboard.Key.space:
        if player.is_playing():
            player.pause()
            print("[USER] Paused")
        else:
            player.play()
            print("[USER] Playing")

def setup_lsl():
    info_time = StreamInfo('Video_Time_Data', 'Time_Markers', 1, 0, 'int32', 'vid_time_stream_001')
    outlet_time = StreamOutlet(info_time)
    
    info_eng = StreamInfo('Engagement_Rating', 'Rating', 1, 0, 'int32', 'vid_rating_stream_001')
    outlet_eng = StreamOutlet(info_eng)
    
    return outlet_time, outlet_eng

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    global waiting_for_input, input_received, current_rating, player

    print("--- STARTING EXPERIMENT ---")
    print("Press SPACE to start/pause video.")
    print("When video pauses automatically, press 1-5 to rate.")

    # 1. Setup LSL
    outlet_time, outlet_eng = setup_lsl()

    # 2. Setup VLC
    if not VIDEO_PATH.exists():
        print(f"CRITICAL ERROR: Video file missing at {VIDEO_PATH}")
        return
        
    vlc_instance = vlc.Instance("--input-repeat=0")
    player = vlc_instance.media_player_new()
    media = vlc_instance.media_new(str(VIDEO_PATH))
    player.set_media(media)
    
    # 3. Setup Audio
    sfx_player = vlc_instance.media_player_new()
    if BEEP_PATH.exists():
        sfx_media = vlc_instance.media_new(str(BEEP_PATH))
        sfx_player.set_media(sfx_media)

    # 4. Start Keyboard Listener
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    # 5. Initialize Window (Start paused)
    player.play()
    time.sleep(0.5) 
    player.set_pause(1) # Immediately pause so user sees first frame
    player.set_fullscreen(True)
    
    last_trigger_second = 0

    try:
        while True:
            # Check for end of video
            if player.get_state() == vlc.State.Ended:
                print("Video Ended.")
                break

            # Get current time
            t_ms = player.get_time()
            if t_ms < 0: t_ms = 0
            seconds = int(t_ms // 1000)

            # --- CHECK TRIGGER CONDITION (Only if playing) ---
            if player.is_playing() and seconds > 0 and seconds % PAUSE_INTERVAL == 0 and seconds != last_trigger_second:
                
                print(f"\n[TRIGGER] 60s Interval Reached at {seconds}s. Pausing...")
                
                # A. Force Pause
                player.set_pause(1)
                
                # B. Play Beep
                if BEEP_PATH.exists():
                    sfx_player.stop()
                    sfx_player.play()
                
                # C. Block until input
                waiting_for_input = True
                input_received = False
                last_trigger_second = seconds 

                # Wait Loop
                while not input_received:
                    # Keep streaming LSL even while waiting
                    outlet_time.push_sample([seconds])
                    outlet_eng.push_sample([current_rating])
                    time.sleep(0.05) 

                # D. Resume
                print("[RESUME] Input received. Resuming...")
                waiting_for_input = False
                player.set_pause(0)

            # --- STANDARD LSL PUSH ---
            outlet_time.push_sample([seconds])
            outlet_eng.push_sample([current_rating])

            time.sleep(0.033)

    except KeyboardInterrupt:
        print("\nExperiment manually stopped.")
    finally:
        player.stop()
        sfx_player.release()
        listener.stop()

if __name__ == "__main__":
    main()