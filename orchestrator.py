from Muse.muse import start_muse_stream
from MSBand.BandReceiver import start_band_receiver
from Beam.beam import start_beam_stream
import threading

band_thread = threading.Thread(target=start_band_receiver)
muse_thread = threading.Thread(target=start_muse_stream)
beam_thread = threading.Thread(target=start_beam_stream)

band_thread.start()
muse_thread.start()
beam_thread.start()