# --- MONKEY PATCH START ---
# Fix for 'BleakClient object has no attribute name' on newer Bleak versions
import bleak

# If the class BleakClient is missing the 'name' property...
if not hasattr(bleak.BleakClient, "name"):
    # ...we inject a fake 'name' property that just returns the device address.
    # This tricks the older library (OpenMuse) into working.
    bleak.BleakClient.name = property(lambda self: self.address)
# --- MONKEY PATCH END ---

import OpenMuse
def start_muse_stream():
    # Find available Muse devices
    devices = OpenMuse.find_muse()
    if not devices:
        print("No Muse devices found.")
        exit(1)

    # Use the first device's MAC address (adjust index if needed for multiple devices)
    address = devices[0]["address"]
    print(f"Streaming from device: {address}")

    # Stream indefinitely to LSL (omit duration for infinite streaming until Ctrl+C)
    # Preset "p1041" enables all channels (EEG, PPG/OPTICS, ACCGYRO, etc.)
    # This creates separate LSL outlets like Muse_EEG, Muse_OPTICS, Muse_ACCGYRO, etc.
    OpenMuse.stream(
        address=address,
        preset="p1041",          # All channels including EEG and OPTICS
        duration=None,           # Indefinite streaming (None = run forever)
        verbose=True,            # Print progress/info
    )