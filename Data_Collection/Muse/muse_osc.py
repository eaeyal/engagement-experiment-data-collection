import argparse
import time
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
from pylsl import StreamInfo, StreamOutlet

# --- HARDCODED CONFIGURATION ---
STREAM_CONFIG = {
    "/muse/eeg": ("muse_eeg", 8, "EEG", "float32"),
    "/muse/optics": ("muse_optics", 16, "PPG", "float32"),
    "/muse/acc": ("muse_acc", 3, "Accel", "float32"),
    "/muse/gyro": ("muse_gyro", 3, "Gyro", "float32"),
    "/muse/elements/alpha_absolute": ("muse_alpha", 4, "Bands", "float32"),
    "/muse/elements/beta_absolute": ("muse_beta", 4, "Bands", "float32"),
    "/muse/elements/delta_absolute": ("muse_delta", 4, "Bands", "float32"),
    "/muse/elements/theta_absolute": ("muse_theta", 4, "Bands", "float32"),
    "/muse/elements/gamma_absolute": ("muse_gamma", 4, "Bands", "float32"),
    "/muse/elements/horseshoe": ("muse_horseshoe", 4, "Quality", "float32"),
    "/muse/batt": ("muse_battery", 4, "Battery", "int32"),
    "/muse/elements/touching_forehead": ("muse_contact", 1, "Markers", "int32"),
    "/muse/elements/blink": ("muse_blink", 1, "Markers", "int32"),
    "/muse/elements/jaw_clench": ("muse_jaw_clench", 1, "Markers", "int32"),
}

outlets = {}
packet_count = 0
start_time = time.time()

def setup_outlets():
    print("--- Initializing LSL Outlets ---")
    for path, config in STREAM_CONFIG.items():
        name, ch_count, st_type, fmt = config
        info = StreamInfo(name, st_type, ch_count, 0.0, fmt)
        outlets[path] = StreamOutlet(info)
        print(f"OK: {path} -> LSL: {name}")
    print("---------------------------------\n")

def relay_handler(address, *args):
    global packet_count
    if address in outlets:
        try:
            outlets[address].push_sample(args)
            packet_count += 1
            
            # Print status message every 100 packets
            if packet_count % 100 == 0:
                elapsed = round(time.time() - start_time, 1)
                print(f"[{elapsed}s] Receiving data... Total packets relayed: {packet_count}", end='\r')
                
        except Exception as e:
            print(f"\nError pushing {address}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="0.0.0.0", help="The ip to listen on")
    parser.add_argument("--port", type=int, default=5000, help="The port to listen on")
    args = parser.parse_args()

    setup_outlets()

    dispatcher = Dispatcher()
    for path in STREAM_CONFIG.keys():
        dispatcher.map(path, relay_handler)

    server = BlockingOSCUDPServer((args.ip, args.port), dispatcher)
    
    print(f"Relay active on {args.ip}:{args.port}.")
    print("Streaming Mind Monitor OSC to LSL. Press Ctrl+C to stop.\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n\nRelay stopped. Total packets processed: {packet_count}")