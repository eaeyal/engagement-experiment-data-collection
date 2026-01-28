import pyxdf
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import butter, filtfilt, iirnotch

def butter_highpass_filter(data, cutoff, fs, order=5):
    """Removes DC drift and slow-wave artifacts."""
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='high', analog=False)
    return filtfilt(b, a, data, axis=0)

def notch_filter(data, f0, fs, Q=30.0):
    """Removes specific frequency interference (e.g., 60Hz line noise)."""
    b, a = iirnotch(f0, Q, fs)
    return filtfilt(b, a, data, axis=0)

def analyze_eeg_xdf(file_path):
    streams, header = pyxdf.load_xdf(file_path)
    
    data_dict = {}
    for stream in streams:
        name = stream['info']['name'][0]
        data_dict[name] = {
            "time": stream['time_stamps'],
            "data": stream['time_series']
        }

    # EEG labels for Muse S
    ch_names = ['TP9', 'AF7', 'AF8', 'TP10']
    
    if 'muse_eeg' not in data_dict:
        print("Error: muse_eeg stream not found in file.")
        return

    eeg_stream = data_dict['muse_eeg']
    eeg_data = eeg_stream['data'][:, :4] 
    eeg_time = eeg_stream['time']
    
    # Calculate effective sampling rate
    fs = 1 / np.mean(np.diff(eeg_time))
    print(f"Effective Sampling Rate: {fs:.2f} Hz")
    
    # --- PIPELINE: HIGH-PASS THEN NOTCH ---
    # 1. High-pass at 1.0Hz to center signal at 0
    
    # 2. Notch filter at 60Hz (typical for North America)
    final_eeg = notch_filter(eeg_data, 60.0, fs)

    # Plotting: 4 EEG + 1 Markers + 1 User Rating = 6 subplots
    fig, axes = plt.subplots(6, 1, figsize=(12, 14), sharex=True)
    
    # 1-4. Plot each EEG channel
    for i in range(4):
        axes[i].plot(eeg_time, final_eeg[:, i], linewidth=0.7, color='black')
        axes[i].set_title(f"EEG Channel: {ch_names[i]} (1Hz Highpass + 60Hz Notch)")
        axes[i].set_ylabel("µV")
        axes[i].grid(True, alpha=0.3)

    # 5. Plot Markers (Blinks/Jaw Clench/Contact)
    axes[4].set_title("Artifact Events (Blinks/Clench)")
    marker_colors = {'muse_blink': 'orange', 'muse_jaw_clench': 'red'}
    
    for stream_name, color in marker_colors.items():
        if stream_name in data_dict:
            m_stream = data_dict[stream_name]
            event_indices = np.where(m_stream['data'] == 1)[0]
            for idx in event_indices:
                t = m_stream['time'][idx]
                axes[4].axvline(x=t, color=color, linestyle='--', 
                                label=stream_name if idx == 0 else "")
    
    axes[4].legend(loc='upper right')
    axes[4].set_yticks([])

    # 6. Plot User Rating (LastNumberStream)
    axes[5].set_title("Self-Reported Engagement Rating (0-5)")
    if 'LastNumberStream' in data_dict:
        rating_stream = data_dict['LastNumberStream']
        axes[5].plot(rating_stream['time'], rating_stream['data'], color='green', linewidth=2, drawstyle='steps-post')
        axes[5].set_ylim(-0.5, 5.5)
        axes[5].set_ylabel("Rating")
        axes[5].grid(True, alpha=0.3)
    else:
        axes[5].text(0.5, 0.5, "LastNumberStream not found", ha='center', va='center')

    axes[5].set_xlabel("Time (LSL Seconds)")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    analyze_eeg_xdf("/Users/edan/engagement-experiment/Data_Processing/data/test_muse.xdf")