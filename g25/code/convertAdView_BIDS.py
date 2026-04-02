#!/usr/bin/env python3
"""
Convert ad viewing task CSV files to BIDS-formatted TSV files.
Input:  ../stimuli/Scan-Passive-Ads/data/*_logs_*.csv
Output: ../bids/sub-*/func/sub-*_task-adview_run-1_events.tsv
"""
import re
from pathlib import Path
import pandas as pd

# Columns that MUST exist in the CSV
REQUIRED_COLUMNS = {
    "timestamp",
    "category",
    "image",
    "sub_category",
    "description",
}


def load_subject_list(sublist_file: Path) -> set:
    """Load subject IDs from a text file (one per line)."""
    if not sublist_file.exists():
        raise FileNotFoundError(f"Subject list not found: {sublist_file.resolve()}")

    subjects = set()
    with open(sublist_file, 'r') as f:
        for line in f:
            sub_id = line.strip()
            if sub_id:  # Skip empty lines
                subjects.add(sub_id.zfill(5))  # Normalize to 5 digits
    return subjects


def extract_subject_id(filename: str) -> str:
    """
    Extract subject ID from the beginning of the filename.
    Examples:
        10033_logs_2025-09-23.csv -> 10033
        2001_logs_2025-09-23.csv  -> 02001
    """
    match = re.match(r"(\d{3,5})", filename)
    if not match:
        raise ValueError(f"Could not extract subject ID from filename: {filename}")
    return match.group(1).zfill(5)


def convert_csv_to_bids(csv_file: Path, bids_root: Path, image_duration: float = 2.0):
    """Convert a single CSV file to a BIDS events TSV."""
    df = pd.read_csv(csv_file)

    # Validate required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"{csv_file.name} is missing columns: {missing}")

    subject_id = extract_subject_id(csv_file.name)

    # Create subject-level func directory
    subject_func_dir = bids_root / f"sub-{subject_id}" / "func"
    subject_func_dir.mkdir(parents=True, exist_ok=True)
    output_file = (
        subject_func_dir
        / f"sub-{subject_id}_task-adview_run-1_events.tsv"
    )

    # Core BIDS-required and task-essential columns
    events = pd.DataFrame({
        "onset": df["timestamp"].astype(float),
        "duration": image_duration,
        "trial_type": df["category"],
        "stimulus_file": df["image"],
        "sub_category": df["sub_category"],
        "description": df["description"],
    })

    # Optional columns (added only if present)
    if "isi_duration" in df.columns:
        events["isi_duration"] = df["isi_duration"]

    if "is_attention_check" in df.columns:
        events["is_attention_check"] = (
            df["is_attention_check"]
            .astype(str)
            .str.lower()
            .isin(["1", "true", "yes"])
            .astype(int)
        )
        # Replace trial_type with "attention_check" where is_attention_check is 1
        events.loc[events["is_attention_check"] == 1, "trial_type"] = "attention_check"

    if "attention_response" in df.columns:
        events["attention_response"] = (
            df["attention_response"]
            .replace(["NA", "NaN", ""], "n/a")
        )
        # Replace trial_type with "missed_trial" where attention_response is "no_response"
        events.loc[df["attention_response"] == "no_response", "trial_type"] = "missed_trial"

    # Sort by onset time
    events = events.sort_values("onset").reset_index(drop=True)

    # Write TSV
    events.to_csv(output_file, sep="\t", index=False, na_rep="n/a")
    print(f"{csv_file.name} → {output_file}")


def main():
    input_dir = Path("../../gambling-2025/stimuli/Scan-Passive-Ads/data")
    bids_root = Path("../bids")
    sublist_file = Path("sublist-new.txt")

    # Load subject list
    subject_list = load_subject_list(sublist_file)
    print(f"Loaded {len(subject_list)} subject(s) from {sublist_file}")

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir.resolve()}")

    bids_root.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(input_dir.glob("*_logs_*.csv"))
    if not csv_files:
        print("No CSV files found.")
        return

    # Filter CSV files to only include subjects in the list
    csv_files_filtered = [
        f for f in csv_files
        if extract_subject_id(f.name) in subject_list
    ]

    print(f"Found {len(csv_files_filtered)} CSV file(s) matching subject list")
    print("-" * 60)

    for csv_file in csv_files_filtered:
        try:
            convert_csv_to_bids(csv_file, bids_root)
        except Exception as e:
            print(f"Error processing {csv_file.name}: {e}")

    print("-" * 60)
    print("Conversion complete.")


if __name__ == "__main__":
    main()
