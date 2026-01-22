from Muse.muse import start_muse_stream
from MSBand.BandReceiver import start_band_receiver
from Beam.beam import start_beam_stream
from Polar.Polar2LSL import start_polar_stream
import threading

polar_thread = threading.Thread(target=start_polar_stream)
band_thread = threading.Thread(target=start_band_receiver)
muse_thread = threading.Thread(target=start_muse_stream)
beam_thread = threading.Thread(target=start_beam_stream)

polar_thread.start()
band_thread.start()
muse_thread.start()
beam_thread.start()