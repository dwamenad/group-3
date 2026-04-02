import json
import os

# Define paths
bidsdir = "/ZPOOL/data/projects/g25/bids/"

# First, handle task-level JSON files in the BIDS root directory
print("Processing task-level JSON files...")
task_json_files = [f for f in os.listdir(bidsdir) if f.startswith('task-') and f.endswith('.json')]

for task_file in task_json_files:
    task_path = os.path.join(bidsdir, task_file)
    
    with open(task_path, 'r') as f:
        data = json.load(f)
    
    # Remove fields that should not be at task level
    fields_to_remove = ['ImageOrientationPatientDICOM', 'ShimSetting']
    removed = []
    
    for field in fields_to_remove:
        if field in data:
            del data[field]
            removed.append(field)
    
    if removed:
        with open(task_path, 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True)
        print(f"  Removed {', '.join(removed)} from {task_file}")
    else:
        print(f"  No changes needed for {task_file}")

print("\nProcessing subject-level files...")

# Find all subject directories in the BIDS directory
subs = [d for d in os.listdir(bidsdir) if os.path.isdir(os.path.join(bidsdir, d)) and d.startswith('sub')]

for subj in subs:
    print("Running subject:", subj)
    
    # Process func, anat, and dwi directories
    for data_type in ['func', 'anat', 'dwi', 'fmap']:
        data_dir = os.path.join(bidsdir, subj, data_type)
        
        # Check if the directory exists
        if not os.path.exists(data_dir):
            continue
        
        # Find all JSON files in this directory
        json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
        
        for json_file in json_files:
            json_path = os.path.join(data_dir, json_file)
            
            with open(json_path, 'r') as f:
                data = json.load(f)
                
                # For func files, handle Units and TaskDescription
                if data_type == 'func' or data_type == 'fmap':
                    if 'bold.json' in json_file or 'sbref.json' in json_file or 'fieldmap.json' in json_file:
                        # Extract task from filename
                        file_parts = json_file.split('_')
                        task = file_parts[1].split('-')[1]
                        
                        # Check the file name for 'part-mag' or 'part-phase' and set units accordingly
                        if 'part-mag' in json_file:
                            data["Units"] = "Hz"
                        elif 'part-phase' in json_file:
                            data["Units"] = "rad"
                        else:
                            data["Units"] = "Hz"  # Default to Hz if neither is found
                        
                        # Add TaskDescription based on task name
                        data["TaskDescription"] = task
                
                # Add InstitutionalDepartmentName to all files
                data["InstitutionalDepartmentName"] = "Department of Neuroscience and Psychology"
            
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=4, sort_keys=True)
            
            print(f"Updated {json_path}")

print("\nDone!")
