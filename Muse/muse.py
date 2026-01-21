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