import os
import glob
import json
import numpy as np

# Path to the JSON files (filtered for echo-2 only)
path = "/ZPOOL/data/projects/g25/derivatives/mriqc/sub-*/func/*echo-2_part-mag_bold.json"

# Find all JSON files
json_files = glob.glob(path)

# Lists to store values
participants = []
tasks = []
runs = []
fd_means = []
tsnrs = []

for file in json_files:
    # Extract info from the filename
    basename = os.path.basename(file)
    parts = basename.split('_')
    participant_id = parts[0].split('-')[1]  # sub-11039 -> 11039
    task = parts[1].split('-')[1]             # task-trust -> trust
    run = parts[2].split('-')[1]              # run-2 -> 2
    
    with open(file, 'r') as f:
        try:
            data = json.load(f)
            fd_mean_str = data.get('fd_mean')
            tsnr_str = data.get('tsnr')
            
            if fd_mean_str is not None and tsnr_str is not None:
                # Convert values from string to float
                fd_mean = float(fd_mean_str)
                tsnr = float(tsnr_str)
                
                # Append values to lists
                participants.append(participant_id)
                tasks.append(task)
                runs.append(run)
                fd_means.append(fd_mean)
                tsnrs.append(tsnr)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error processing file {file}: {str(e)}")

# Combine into list of tuples and sort by task, then by run (ascending)
combined = list(zip(participants, tasks, runs, fd_means, tsnrs))
combined_sorted = sorted(combined, key=lambda x: (x[1], int(x[2])))

# Print the results in tabular format
print("Participant ID\tTask\t\tRun\tfd_mean\t\ttsnr")
print("-------------------------------------------------------------")
for participant_id, task, run, fd_mean, tsnr in combined_sorted:
    print(f"{participant_id}\t\t{task}\t\t{run}\t{fd_mean:.4f}\t\t{tsnr:.2f}")
