from pathlib import Path
import pyxdf
import numpy as np
import matplotlib.pyplot as plt

XDF_PATH = Path(__file__).parent / "test3.xdf"  # <- change this

# Load XDF
streams, header = pyxdf.load_xdf(XDF_PATH)

print(f"Loaded {len(streams)} streams")

def plot_stream(stream, title):
    data = stream["time_series"]
    ts = stream["time_stamps"]

    data = np.asarray(data)

    if data.ndim == 1:
        data = data[:, None]

    n_ch = data.shape[1]

    fig, axes = plt.subplots(n_ch, 1, sharex=True, figsize=(12, 2.5 * n_ch))
    if n_ch == 1:
        axes = [axes]

    for ch in range(n_ch):
        axes[ch].plot(ts, data[:, ch])
        axes[ch].set_ylabel(f"Ch {ch}")
        axes[ch].grid(True)

    axes[-1].set_xlabel("Time (s)")
    fig.suptitle(title)
    plt.tight_layout()
    plt.show()


# Iterate streams
for s in streams:
    name = s["info"]["name"][0]
    stype = s["info"]["type"][0]
 
    ts = s["time_stamps"]
    fs = 1.0 / np.median(np.diff(ts))
    print(f"  Estimated Fs: {fs:.2f} Hz")

    print(f"Plotting stream: {name} ({stype})")

    # ---- PPG ----
    if name == "OmniBuds_PPG":
        plot_stream(s, "OmniBuds PPG (Green / Red / IR)")

    # ---- Accelerometer ----
    elif name == "OmniBuds_Accel":
        plot_stream(s, "OmniBuds Accelerometer (X Y Z)")

    # ---- Gyroscope ----
    elif name == "OmniBuds_Gyro":
        plot_stream(s, "OmniBuds Gyroscope (X Y Z)")

    # ---- Magnetometer ----
    elif name == "OmniBuds_Mag":
        plot_stream(s, "OmniBuds Magnetometer (X Y Z)")
