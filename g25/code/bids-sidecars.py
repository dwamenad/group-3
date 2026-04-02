#!/usr/bin/env python3
"""
Create JSON sidecar files for BIDS events.tsv files.

Searches for events.tsv files for tasks: trust, SST, and adview
Creates corresponding .json files with column descriptions.

Input: ../bids/**/sub-*_task-*_run-*_events.tsv
Output: ../bids/**/sub-*_task-*_run-*_events.json
"""

import json
from pathlib import Path


# Define column descriptions for each task
TASK_DESCRIPTIONS = {
    'adview': {
        'onset': {
            'LongName': 'Event onset',
            'Description': 'Onset time of the event in seconds relative to the start of the recording',
            'Units': 's'
        },
        'duration': {
            'LongName': 'Event duration',
            'Description': 'Duration of the stimulus presentation',
            'Units': 's'
        },
        'trial_type': {
            'LongName': 'Trial type',
            'Description': 'Category of the stimulus (Gambling, Every_day_products, vmPFC)',
            'Levels': {
                'Gambling': 'Gambling-related advertisement',
                'Every_day_products': 'Everyday consumer products',
                'vmPFC': 'vmPFC-related stimuli (luxury goods, vacation, outdoor activities, games, amusement)'
            }
        },
        'stimulus_file': {
            'LongName': 'Stimulus filename',
            'Description': 'Filename of the image stimulus presented'
        },
        'sub_category': {
            'LongName': 'Subcategory',
            'Description': 'Subcategory of the stimulus (e.g., Mobile, Casino, Necessities, Luxury_Goods, Outdoors, Vacation, Amusement, Games)'
        },
        'description': {
            'LongName': 'Stimulus description',
            'Description': 'Detailed description of the specific stimulus/brand'
        },
        'isi_duration': {
            'LongName': 'Inter-stimulus interval duration',
            'Description': 'Duration of the fixation period following the stimulus',
            'Units': 's'
        },
        'is_attention_check': {
            'LongName': 'Attention check trial',
            'Description': 'Whether this trial was an attention check',
            'Levels': {
                '0': 'Not an attention check',
                '1': 'Attention check trial'
            }
        },
        'attention_response': {
            'LongName': 'Attention check response',
            'Description': 'Response given on attention check trials',
            'Levels': {
                'n/a': 'Not an attention check trial',
                'pressed_2': 'Correct response (button 2 pressed)',
                'no_response': 'No response given'
            }
        }
    },
    
    'SST': {
        'onset': {
            'LongName': 'Event onset',
            'Description': 'Onset time of the event in seconds relative to the start of the recording',
            'Units': 's'
        },
        'duration': {
            'LongName': 'Event duration',
            'Description': 'Duration of the event',
            'Units': 's'
        },
        'trial_type': {
            'LongName': 'Trial and outcome type',
            'Description': 'Type of trial and outcome in the Stop Signal Task',
            'Levels': {
                'go_correct': 'Go trial with correct response',
                'go_incorrect': 'Go trial with incorrect response',
                'go_miss': 'Go trial with no response',
                'stop_success': 'Stop trial with successful inhibition',
                'stop_failure': 'Stop trial with failed inhibition',
                'fixation': 'Fixation period'
            }
        },
        'response_time': {
            'LongName': 'Response time',
            'Description': 'Reaction time in seconds (n/a for missed trials and fixations)',
            'Units': 's'
        },
        'ssd': {
            'LongName': 'Stop signal delay',
            'Description': 'Delay between go stimulus and stop signal in milliseconds (n/a for go trials)',
            'Units': 'ms'
        }
    },
    
    'trust': {
        'onset': {
            'LongName': 'Event onset',
            'Description': 'Onset time of the event in seconds relative to the start of the recording',
            'Units': 's'
        },
        'duration': {
            'LongName': 'Event duration',
            'Description': 'Duration of the event',
            'Units': 's'
        },
        'trial_type': {
            'LongName': 'Trial and outcome type',
            'Description': 'Type of trial or outcome',
            'Levels': {
                'choice_close_good': '',
                'choice_close_bad': '',
                'choice_far_good': '',
                'choice_far_bad': '',
                'outcome_close_good_recip': '',
                'outcome_close_bad_recip': '',
                'outcome_far_good_recip': '',
                'outcome_far_bad_recip': '',
                'outcome_close_good_defect': '',
                'outcome_close_bad_defect': '',
                'outcome_far_good_defect': '',
                'outcome_far_bad_defect': '',
                'missed_trial': ''
            }
        },
        'response_time': {
            'LongName': 'Response time',
            'Description': 'Time it took participant to respond during choice phase in seconds',
            'Units': 's'
        },
        'trust_value': {
            'LongName': 'Amount the participant invested in USD ($)',
            'Description': 'Amount invested by the participant',
            'Levels': {
                '0': '$0.00',
                '4': '$4.00',
                '10': '$10.00',
                '16': '$16.00',
                '20': '$20.00'
            }
        },
        'choice': {
            'LongName': 'Participant investment choice',
            'Description': 'Whether the participant chose the higher or lower option of the two possible choices',
            'Levels': {
                'low': 'The lower value of the two choices',
                'high': 'The higher value of the two choices'
            }

        },
        'cLow': {
            'LongName': 'Choice low',
            'Description': 'USD ($) Amount of the lower choice of the two possible choices',
            'Levels': {
                '0': '$0.00',
                '4': '$4.00',
                '10': '$10.00',
                '16': '$16.00'
            }
        },
        'cHigh': {
            'LongName': 'Choice high',
            'Description': 'USD ($) Amount of the higher choice of the two possible choices',
            'Levels': {
                '4': '$4.00',
                '6': '$6.00',
                '10': '$10.00',
                '16': '$16.00',
                '20': '$20.00'
            }
        }
    }
}


def create_json_sidecar(tsv_file, task_name):
    """
    Create a JSON sidecar file for a given events.tsv file.
    
    Parameters:
    -----------
    tsv_file : Path
        Path to the events.tsv file
    task_name : str
        Name of the task (trust, SST, adview)
    """
    # Define output JSON file path
    json_file = tsv_file.with_suffix('.json')
    
    # Get the appropriate column descriptions for this task
    if task_name not in TASK_DESCRIPTIONS:
        print(f"Warning: Unknown task '{task_name}' - skipping {tsv_file.name}")
        return
    
    columns = TASK_DESCRIPTIONS[task_name]
    
    # Write JSON sidecar
    with open(json_file, 'w') as f:
        json.dump(columns, f, indent=2)
    
    print(f"Created: {json_file.name}")


def main():
    """Main function to create JSON sidecars for all events files"""
    
    # Define base path
    bids_dir = Path('../bids')
    
    if not bids_dir.exists():
        print(f"Error: BIDS directory not found: {bids_dir.resolve()}")
        return
    
    print("Creating JSON sidecars for BIDS events files")
    print("=" * 60)
    
    # Process each task
    tasks = ['trust', 'SST', 'adview']
    total_created = 0
    
    for task in tasks:
        print(f"\nTask: {task}")
        print("-" * 60)
        
        # Find all events.tsv files for this task
        tsv_files = list(bids_dir.rglob(f'*_task-{task}_*_events.tsv'))
        
        if not tsv_files:
            print(f"No events files found for task '{task}'")
            continue
        
        print(f"Found {len(tsv_files)} events file(s)")
        
        # Create JSON sidecar for each TSV file
        for tsv_file in sorted(tsv_files):
            create_json_sidecar(tsv_file, task)
            total_created += 1
    
    print("\n" + "=" * 60)
    print(f"Created {total_created} JSON sidecar file(s)")


if __name__ == "__main__":
    main()
