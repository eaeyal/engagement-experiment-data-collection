import asyncio
import sys
from pylsl import StreamInfo, StreamOutlet
from bleak import BleakClient
from bleak.uuids import uuid16_dict

# --- Configuration & Constants ---
# You can change these defaults or pass them as arguments to start_polar_stream
import sys
# Detect OS to choose the correct address
if sys.platform == "darwin":
    # Mac UUID (Specific to this Mac only)
    DEFAULT_ADDRESS = "00F648B4-C978-51AA-2733-8173896C4FE8"
else:
    # Windows MAC Address
    DEFAULT_ADDRESS = "24:AC:AC:07:02:48"

DEFAULT_STREAM_NAME = 'PolarBand'
DEFAULT_STREAM_NAME = 'PolarBand'

# UUID Definitions
uuid16_dict = {v: k for k, v in uuid16_dict.items()}
PMD_CONTROL = "FB005C81-02E7-F387-1CAD-8ACD2D8DF0C8"
PMD_DATA = "FB005C82-02E7-F387-1CAD-8ACD2D8DF0C8"

# Commands
ECG_WRITE = bytearray([0x02, 0x00, 0x00, 0x01, 0x82, 0x00, 0x01, 0x01, 0x0E, 0x00])
ECG_SAMPLING_FREQ = 130

# Module-level variable to hold the LSL outlet
_OUTLET = None

def _setup_lsl(name):
    """Helper to configure the LSL stream."""
    info = StreamInfo(name, 'ECG', 1, ECG_SAMPLING_FREQ, 'float32', 'polar_id_1234')
    info.desc().append_child_value("manufacturer", "Polar")
    channels = info.desc().append_child("channels")
    channels.append_child("channel") \
            .append_child_value("name", "ECG") \
            .append_child_value("unit", "microvolts") \
            .append_child_value("type", "ECG")
    return StreamOutlet(info, 74, 360)

def _data_handler(sender, data: bytearray):
    """Callback for Bleak when data arrives."""
    global _OUTLET
    if data[0] == 0x00:
        step = 3
        samples = data[10:]
        offset = 0
        while offset < len(samples):
            val = int.from_bytes(samples[offset : offset + step], byteorder="little", signed=True)
            offset += step
            if _OUTLET:
                _OUTLET.push_sample([val])

async def _async_worker(address):
    """The async logic that connects and keeps the stream open."""
    print(f"[Polar] Connecting to {address}...", flush=True)
    
    async with BleakClient(address) as client:
        if not client.is_connected:
            print("[Polar] Failed to connect.", flush=True)
            return

        print("[Polar] Connected.", flush=True)

        # 1. Subscribe FIRST (Critical fix for reliability)
        await client.start_notify(PMD_DATA, _data_handler)
        await asyncio.sleep(0.5)

        # 2. Write Start Command SECOND
        await client.write_gatt_char(PMD_CONTROL, ECG_WRITE)
        print("[Polar] Stream started.", flush=True)

        # 3. Run indefinitely
        # This keeps the context manager open and the connection alive
        while True:
            await asyncio.sleep(1.0)

def start_polar_stream(address=DEFAULT_ADDRESS, stream_name=DEFAULT_STREAM_NAME):
    """
    The entry point. Call this function as the target of your threading.Thread.
    """
    global _OUTLET
    
    # 1. Setup LSL
    print(f"[Polar] Init LSL Stream: {stream_name}", flush=True)
    _OUTLET = _setup_lsl(stream_name)

    # 2. Setup Asyncio for this thread
    # Since this runs in a new thread, we must explicitly create a new loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # 3. Run the async worker
        loop.run_until_complete(_async_worker(address))
    except Exception as e:
        print(f"[Polar] Error: {e}", flush=True)
    finally:
        loop.close()
if __name__ == "__main__":
    start_polar_stream()