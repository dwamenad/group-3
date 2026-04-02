#!/usr/bin/env python3
"""
Convert SST task CSV files to BIDS-formatted TSV files.

Input: ../stimuli/Scan-SST/logs/sub-#####/sub-#####_task-SST_run-#_events.csv
Output: ../bids/sub-#####/func/sub-#####_task-SST_run-#_events.tsv

Creates BIDS-compliant events files with:
- onset: event onset time in seconds
- duration: event duration in seconds
- trial_type: type of trial (go_correct, go_incorrect, go_miss, stop_success, stop_failure)
- response_time: reaction time in seconds (for response trials)
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path


def determine_trial_type(row):
    """
    Determine trial type based on Stop Signal Task conditions.
    
    Parameters:
    -----------
    row : pandas Series
        Row from the events dataframe
    
    Returns:
    --------
    str : trial type label
    """
    # For task trials, check stop vs go and outcome
    if row['stop'] == 1:
        # Stop trial
        if row['stop_success'] == 1:
            return 'stop_success'
        else:
            return 'stop_failure'
    else:
        # Go trial (stop == 0)
        if row['go_miss'] == 1:
            return 'go_miss'
        elif row['go_correct'] == 1:
            return 'go_correct'
        elif row['go_incorrect'] == 1:
            return 'go_incorrect'
        else:
            return 'unknown'
    
    return 'unknown'


def convert_subject_events(subject_id, input_base, output_base):
    """
    Convert all runs for a single subject from CSV to BIDS TSV format.
    
    Parameters:
    -----------
    subject_id : str
        5-digit subject ID (e.g., '00001')
    input_base : str
        Base path to input CSV files
    output_base : str
        Base path to output TSV files
    """
    # Define paths
    input_dir = Path(input_base) / f"sub-{subject_id}"
    output_dir = Path(output_base) / f"sub-{subject_id}" / "func"
    
    # Check if input directory exists
    if not input_dir.exists():
        print(f"Warning: Input directory not found for sub-{subject_id}: {input_dir}")
        return
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all CSV files for this subject
    csv_files = list(input_dir.glob(f"sub-{subject_id}_task-SST_run-*_events.csv"))
    
    if not csv_files:
        print(f"Warning: No CSV files found for sub-{subject_id}")
        return
    
    # Process each run
    for csv_file in sorted(csv_files):
        # Extract run number from filename
        run_num = csv_file.stem.split('run-')[1].split('_')[0]
        
        # Define output filename
        output_file = output_dir / f"sub-{subject_id}_task-SST_run-{run_num}_events.tsv"
        
        try:
            # Read CSV file (comma-separated)
            df = pd.read_csv(csv_file)  # Default separator is comma
            
            # Remove rows where stim_onset is missing (these are not actual trials)
            df = df[df['stim_onset'].notna()].copy()
            
            # Create lists to store all events (trials + fixations)
            events_list = []
            
            # Process each trial and add fixation periods
            for idx, row in df.iterrows():
                # Add fixation event if ISI/ITI information is available
                if 'isi_onset' in df.columns and pd.notna(row['isi_onset']):
                    # Calculate fixation duration from ISI and ITI
                    fixation_onset = row['isi_onset']
                    
                    # Fixation ends when stimulus starts
                    fixation_duration = row['stim_onset'] - row['isi_onset'] if pd.notna(row['stim_onset']) else 0
                    
                    # Add fixation event
                    if fixation_duration > 0:
                        events_list.append({
                            'onset': fixation_onset,
                            'duration': fixation_duration,
                            'trial_type': 'fixation',
                            'response_time': np.nan,
                            'ssd': np.nan
                        })
                
                # Determine trial type
                trial_type = determine_trial_type(row)
                
                # For missed trials (go_miss), set response_time to NaN
                if trial_type == 'go_miss':
                    response_time = np.nan
                else:
                    response_time = row['rt'] if 'rt' in df.columns and pd.notna(row['rt']) else np.nan
                
                # Add the actual trial event
                events_list.append({
                    'onset': row['stim_onset'],
                    'duration': row['duration'] if 'duration' in df.columns else 0,
                    'trial_type': trial_type,
                    'response_time': response_time,
                    'ssd': row['ssd'] * 1000 if 'ssd' in df.columns and pd.notna(row['ssd']) else np.nan
                })
            
            # Create BIDS events dataframe from the events list
            bids_events = pd.DataFrame(events_list)
            
            # Sort by onset time
            bids_events = bids_events.sort_values('onset').reset_index(drop=True)
            
            # Write to TSV file (use 'n/a' for missing values per BIDS standard)
            bids_events.to_csv(output_file, sep='\t', index=False, na_rep='n/a')
            
            print(f"Converted: sub-{subject_id} run-{run_num} -> {output_file} ({len(bids_events)} events)")
            
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main function to process all subjects from sublist.txt"""
    
    # Define paths
    sublist_file = "sublist-new.txt"
    input_base = "../../gambling-2025/stimuli/Scan-SST/logs"
    output_base = "../bids"
    
    # Check if subject list exists
    if not os.path.exists(sublist_file):
        print(f"Error: Subject list file not found: {sublist_file}")
        return
    
    # Read subject list
    with open(sublist_file, 'r') as f:
        subjects = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(subjects)} subjects in {sublist_file}")
    print(f"Input directory: {input_base}")
    print(f"Output directory: {output_base}")
    print("-" * 60)
    
    # Process each subject
    for subject_id in subjects:
        convert_subject_events(subject_id, input_base, output_base)
    
    print("-" * 60)
    print("Conversion complete!")


if __name__ == "__main__":
    main()
