% 1. SETUP & LOAD
clear; clc;
file_path = '/Users/edan/engagement-experiment/Data_Processing/data/muse_random_blink.xdf';
disp('Loading Data...');
[ALLEEG, EEG_Source, CURRENTSET] = eeglab;
EEG_Source = pop_loadxdf(file_path, 'streamtype', 'EEG', 'exclude_markerstreams', {});
EEG_Source = pop_select(EEG_Source, 'channel', 1:4);

% Label Channels
EEG_Source.chanlocs(1).labels = 'TP9'; EEG_Source.chanlocs(2).labels = 'AF7';
EEG_Source.chanlocs(3).labels = 'AF8'; EEG_Source.chanlocs(4).labels = 'TP10';
EEG_Source = pop_chanedit(EEG_Source, 'lookup', 'standard_1005.elc');

% ---------------------------------------------------------
% 2. GENERATE COLUMNS (INDEPENDENT PIPELINES)
% ---------------------------------------------------------

% --- COL 1: RAW ---
COL{1} = EEG_Source;

% --- COL 2: NOTCH ONLY ---
disp('Col 2: Notch...');
COL{2} = pop_eegfiltnew(EEG_Source, 'locutoff', 55, 'hicutoff', 65, 'revfilt', 1);

% --- COL 3: NOTCH + HP ---
disp('Col 3: Notch + HP...');
temp_notch = pop_eegfiltnew(EEG_Source, 'locutoff', 55, 'hicutoff', 65, 'revfilt', 1);
COL{3} = pop_clean_rawdata(temp_notch, 'FlatlineCriterion','off', 'ChannelCriterion','off', ...
    'LineNoiseCriterion','off', 'Highpass', [0.25 0.75], 'BurstCriterion','off', ...
    'WindowCriterion','off', 'BurstRejection','off', 'Distance','Euclidian');

% --- COL 4: NOTCH + HP + BURST (REPAIR) ---
disp('Col 4: Notch + HP + Burst...');
COL{4} = pop_clean_rawdata(COL{3}, 'FlatlineCriterion','off', 'ChannelCriterion','off', ...
    'LineNoiseCriterion','off', 'Highpass', 'off', 'BurstCriterion', 20, ...
    'BurstRejection', 'off', 'WindowCriterion', 'off', 'Distance', 'Euclidian');

% --- COL 5: NOTCH + HP + WINDOW (DELETE) ---
disp('Col 5: Notch + HP + Window...');
COL{5} = pop_clean_rawdata(COL{3}, 'FlatlineCriterion','off', 'ChannelCriterion','off', ...
    'LineNoiseCriterion','off', 'Highpass', 'off', 'BurstCriterion', 'off', ...
    'WindowCriterion', 0.25, 'BurstRejection', 'on', 'Distance', 'Euclidian');

% --- COL 6: FULL STACK ---
disp('Col 6: Full Stack...');
COL{6} = pop_clean_rawdata(COL{3}, 'FlatlineCriterion','off', 'ChannelCriterion','off', ...
    'LineNoiseCriterion','off', 'Highpass', 'off', 'BurstCriterion', 20, ...
    'BurstRejection', 'off', 'WindowCriterion', 0.25, 'Distance', 'Euclidian');

% ---------------------------------------------------------
% 3. VISUALIZE (5 ROWS x 6 COLUMNS)
% ---------------------------------------------------------
disp('Plotting...');
chan_labels = {'TP9', 'AF7', 'AF8', 'TP10'};
titles = {'1. Raw', '2. Notch', '3. +HP', '4. +Burst', '5. +Window', '6. Full'};
colors = {'k', 'c', 'r', 'b', 'm', 'g'}; 

figure('Name', 'Independent Pipelines w/ Artifact Detection', 'Color', 'w', 'Position', [10, 10, 1800, 1100]);

for d = 1:6
    this_EEG = COL{d};
    plot_samples = min(this_EEG.pnts, 30 * this_EEG.srate);
    t_axis = this_EEG.times(1:plot_samples) / 1000;
    
    % --- ROWS 1-4: EEG DATA ---
    for row = 1:4
        subplot(5, 6, (row-1)*6 + d);
        current_samples = min(plot_samples, size(this_EEG.data, 2));
        plot(t_axis(1:current_samples), this_EEG.data(row, 1:current_samples), 'Color', colors{d});
        
        grid on; axis tight;
        if row == 1, title(titles{d}); end
        if d == 1
            ylabel(chan_labels{row});
        elseif d > 2
            ylim([-150 150]);
        end
    end
    
    % --- ROW 5: ARTIFACT DETECTION MASK (1/0) ---
    subplot(5, 6, 4*6 + d);
    
    if d == 4 || d == 6
        % ASR Repair detection: Compare against HP-only (COL 3)
        % If the values are different, ASR was active.
        diff_signal = abs(COL{3}.data(1:4, 1:plot_samples) - this_EEG.data(1:4, 1:plot_samples));
        % If any channel was modified at this time point, flag it as 1
        mask = any(diff_signal > 1e-6, 1); 
        fill_color = [1 0.8 0.8]; % Reddish for repair
    elseif d == 5
        % Window Deletion detection: Check for 'boundary' events or data gaps
        % We look for where data in COL 5 is missing compared to COL 3
        % Since COL 5 deletes samples, we visualize where the timeline breaks
        mask = ones(1, plot_samples); % For column 5, the samples that exist are 1
        fill_color = [0.8 1 0.8]; % Greenish for "Still Exists"
    else
        % No artifact processing in Col 1, 2, 3
        mask = zeros(1, plot_samples);
        fill_color = [0.9 0.9 0.9];
    end
    
    area(t_axis(1:length(mask)), mask, 'FaceColor', fill_color, 'EdgeColor', 'none');
    ylim([0 1.2]); yticks([0 1]);
    grid on;
    if d == 1, ylabel('Artf. Flag'); end
    xlabel('Time (s)');
end