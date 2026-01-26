from Muse.muse import start_muse_stream
from MSBand.BandReceiver import start_band_receiver
from Beam.beam import start_beam_stream
from User_Ratings.user_rate import start_user_rating_stream
from Video_Playback.play_video_lsl import start_video_playback_lsl
from lsl import start_lsl_monitor
import threading

band_thread = threading.Thread(target=start_band_receiver)
beam_thread = threading.Thread(target=start_beam_stream)
user_rating_thread = threading.Thread(target=start_user_rating_stream)
video_thread = threading.Thread(target=start_video_playback_lsl)
lsl_monitor_thread = threading.Thread(target=start_lsl_monitor)

band_thread.start()
beam_thread.start()
user_rating_thread.start()
video_thread.start()
lsl_monitor_thread.start()