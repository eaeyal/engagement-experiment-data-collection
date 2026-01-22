import pyxdf
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, find_peaks

# -------------------------
# LOAD XDF
# -------------------------
XDF_PATH = "sub-P001\ses-S001\eeg\sub-P001_ses-S001_task-Default_run-001_eeg.xdf"   # <-- change if needed

streams, header = pyxdf.load_xdf(XDF_PATH)

# -------------------------
# FIND ECG STREAM
# -------------------------
ecg_stream = None

for s in streams:
    info = s["info"]
    ch_type = info["type"][0].lower()
    ch_count = int(info["channel_count"][0])

    if ch_type == "ecg" and ch_count == 1:
        ecg_stream = s
        break

if ecg_stream is None:
    raise RuntimeError("No 1-channel ECG stream found")

# -------------------------
# EXTRACT DATA
# -------------------------
ecg = np.asarray(ecg_stream["time_series"]).flatten()
timestamps = np.asarray(ecg_stream["time_stamps"])

duration = timestamps[-1] - timestamps[0]
fs_est = len(ecg) / duration

print(f"Samples: {len(ecg)}")
print(f"Duration: {duration:.2f} s")
print(f"Estimated Fs: {fs_est:.2f} Hz")

# -------------------------
# CLEAN SIGNAL
# -------------------------
def bandpass_ecg(x, fs, low=0.5, high=40, order=4):
    nyq = 0.5 * fs
    b, a = butter(order, [low/nyq, high/nyq], btype="band")
    return filtfilt(b, a, x)

fs = round(fs_est)
ecg_filt = bandpass_ecg(ecg, fs)

# -------------------------
# R-PEAK DETECTION
# -------------------------
min_rr = 0.35   # seconds
distance = int(min_rr * fs)

peaks, props = find_peaks(
    ecg_filt,
    distance=distance,
    prominence=np.std(ecg_filt)
)

peak_times = timestamps[peaks]
rr = np.diff(peak_times)
hr = 60.0 / rr

print(f"Detected beats: {len(peaks)}")
print(f"Mean HR: {np.mean(hr):.1f} BPM")

# -------------------------
# BASIC HRV (if enough data)
# -------------------------
if len(rr) >= 5:
    rmssd = np.sqrt(np.mean(np.diff(rr) ** 2))
    sdnn = np.std(rr)
    print(f"RMSSD: {rmssd*1000:.1f} ms")
    print(f"SDNN: {sdnn*1000:.1f} ms")
else:
    print("Not enough beats for HRV metrics")

# -------------------------
# PLOTTING
# -------------------------
plt.figure(figsize=(12, 6))

plt.subplot(2, 1, 1)
plt.plot(timestamps, ecg, alpha=0.4, label="Raw ECG")
plt.plot(timestamps, ecg_filt, label="Filtered ECG", linewidth=1)
plt.scatter(peak_times, ecg_filt[peaks], c="r", s=18, label="R-peaks")
plt.ylabel("µV")
plt.legend()
plt.title("Polar H10 ECG")

plt.subplot(2, 1, 2)
plt.plot(hr, marker="o")
plt.ylabel("BPM")
plt.xlabel("Beat index")
plt.title("Instantaneous Heart Rate")

plt.tight_layout()
plt.show()
