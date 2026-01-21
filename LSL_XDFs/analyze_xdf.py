import pyxdf
import pandas as pd
import matplotlib.pyplot as plt
import mne  # For EEG-like data; pip install mne if needed
import numpy as np
from pathlib import Path

# Path to your XDF file (update as needed)
xdf_file = str(Path(__file__).parent / 'sub-P001_ses-S001_task-Default_run-001_eeg.xdf')

# Load the XDF file
streams, header = pyxdf.load_xdf(xdf_file)

# Normalize timestamps across all streams (subtract global min to start at 0)
all_times = np.concatenate([s['time_stamps'] for s in streams if len(s['time_stamps']) > 0])
global_min_time = np.min(all_times) if len(all_times) > 0 else 0.0

for stream in streams:
    stream_name = stream['info']['name'][0]
    timestamps = stream['time_stamps'] - global_min_time  # Normalize
    data = stream['time_series'].T  # Channels x Samples (transpose if needed)
    sfreq = float(stream['info']['nominal_srate'][0]) if stream['info']['nominal_srate'][0] != '0' else None  # 0 means irregular
    
    # Get channel names
    try:
        ch_names = [ch['label'][0] for ch in stream['info']['desc'][0]['channels'][0]['channel']]
    except:
        ch_names = [f'Ch{i+1}' for i in range(data.shape[0])]
    
    # Create DataFrame for table view
    df = pd.DataFrame(data.T, columns=ch_names)  # Samples x Channels
    df.insert(0, 'time', timestamps)
    
    # Print table: First few rows
    print(f"\nTable for Stream: {stream_name}")
    print(df.head())
    
    # Visualize graph
    if sfreq and 'EEG' in stream_name.upper():  # Use MNE for EEG streams
        info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types='eeg')
        raw = mne.io.RawArray(data, info)
        raw.plot(duration=10, scalings='auto', title=f'{stream_name} Data (Normalized Time)')
    else:
        # General matplotlib plot for other streams
        fig, axs = plt.subplots(len(ch_names), 1, figsize=(12, 2 * len(ch_names)), sharex=True)
        if len(ch_names) == 1:
            axs = [axs]
        for i, ax in enumerate(axs):
            ax.plot(timestamps, data[i], label=ch_names[i])
            ax.set_ylabel(ch_names[i])
            ax.legend()
        axs[-1].set_xlabel('Normalized Time (s)')
        plt.suptitle(f'{stream_name} Data')
        plt.tight_layout()
        plt.show()

# Note: For irregular streams (sfreq=0), plots may show uneven spacing, but normalization still aligns them.