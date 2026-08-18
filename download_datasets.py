"""
OmniEar dataset downloader.

Pulls and organizes:
- SESA (Sound Events for Surveillance Applications): gunshot, explosion, siren, casual
- ESC-50 (Environmental Sound Classification): glass breaking, siren, car horn, engine,
  plus background/negative classes

Target class mapping for OmniEar:
    1. scream_distress   -> NOT covered by these two datasets, see note at bottom
    2. explosion          -> SESA "explosion"
    3. impact_crash        -> ESC-50 "glass_breaking" (+ SESA gunshot as impact-transient proxy)
    4. siren_traffic       -> SESA "siren" + ESC-50 "siren"/"car_horn"/"engine"
    5. background           -> SESA "casual" + ESC-50 misc negative classes

Run this from your project root: python download_datasets.py
"""

import os
import zipfile
import shutil
import urllib.request
import csv

DATA_DIR = "data"
RAW_DIR = os.path.join(DATA_DIR, "_raw")
ORGANIZED_DIR = os.path.join(DATA_DIR, "organized")

ESC50_ZIP_URL = "https://github.com/karolpiczak/ESC-50/archive/master.zip"
SESA_ZIP_URL = "https://zenodo.org/records/3519845/files/SESA.zip"

# ESC-50 classes we care about, mapped to our target classes
ESC50_CLASS_MAP = {
    "fireworks": "explosion",
    "glass_breaking": "impact_crash",
    "siren": "siren_traffic",
    "car_horn": "siren_traffic",
    "engine": "siren_traffic",
    "crying_baby": "background",       # not scream, kept as background/negative example
    "footsteps": "background",
    "rain": "background",
    "wind": "background",
    "chainsaw": "background",          # loud but not a threat class -- good hard negative
    "clapping": "background",
    "coughing": "background",
    "door_wood_knock": "background",
    "vacuum_cleaner": "background",
    # Loud hard negatives that are commonly confused with demo threats.
    "thunderstorm": "background",
    "clock_alarm": "background",
    "church_bells": "background",
    "laughing": "background",
    "rooster": "background",
    "dog": "background",
    "cat": "background",
    "hand_saw": "background",
}


def download_file(url, dest_path):
    if os.path.exists(dest_path):
        print(f"Already downloaded: {dest_path}")
        return
    print(f"Downloading {url} ...")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    urllib.request.urlretrieve(url, dest_path)
    print(f"Saved to {dest_path}")


def extract_zip(zip_path, extract_to):
    print(f"Extracting {zip_path} ...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_to)
    print(f"Extracted to {extract_to}")


def organize_esc50():
    esc50_root = None
    for name in os.listdir(RAW_DIR):
        if name.startswith("ESC-50"):
            esc50_root = os.path.join(RAW_DIR, name)
            break
    if esc50_root is None:
        print("ESC-50 folder not found after extraction, skipping.")
        return

    meta_path = os.path.join(esc50_root, "meta", "esc50.csv")
    audio_dir = os.path.join(esc50_root, "audio")

    if not os.path.exists(meta_path):
        print(f"ESC-50 meta file not found at {meta_path}, skipping.")
        return

    count = 0
    with open(meta_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            category = row["category"]
            if category not in ESC50_CLASS_MAP:
                continue
            target_class = ESC50_CLASS_MAP[category]
            src = os.path.join(audio_dir, row["filename"])
            dest_dir = os.path.join(ORGANIZED_DIR, target_class)
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, f"esc50_{row['filename']}")
            if os.path.exists(src):
                shutil.copy2(src, dest)
                count += 1
    print(f"Organized {count} ESC-50 clips into {ORGANIZED_DIR}")


def organize_sesa():
    sesa_root = None
    for name in os.listdir(RAW_DIR):
        if name.upper().startswith("SESA"):
            sesa_root = os.path.join(RAW_DIR, name)
            break
    if sesa_root is None:
        print("SESA folder not found after extraction, skipping.")
        return

    # SESA class labels are typically prefixed in filenames or in subfolders
    # depending on release; handle both train/ and test/ splits, merge for our purposes
    # since we'll do our own split later.
    sesa_class_map = {
        "gun_shot": "impact_crash",
        "gunshot": "impact_crash",
        "explosion": "explosion",
        "siren": "siren_traffic",
        "casual": "background",
    }

    count = 0
    # The current Zenodo archive is nested as SESA/SESA/{train,test}, while
    # older releases placed the split folders directly at the root. Walking
    # makes the downloader work with both layouts and removes the need for a
    # separate one-off repair step.
    for split_dir, _, filenames in os.walk(sesa_root):
        split = os.path.basename(split_dir).lower()
        if split not in {"train", "test"}:
            continue
        for fname in filenames:
            if not fname.lower().endswith(".wav"):
                continue
            lower_name = fname.lower()
            matched_class = None
            for key, target in sesa_class_map.items():
                if key in lower_name:
                    matched_class = target
                    break
            if matched_class is None:
                continue
            dest_dir = os.path.join(ORGANIZED_DIR, matched_class)
            os.makedirs(dest_dir, exist_ok=True)
            src = os.path.join(split_dir, fname)
            dest = os.path.join(dest_dir, f"sesa_{split}_{fname}")
            shutil.copy2(src, dest)
            count += 1
    print(f"Organized {count} SESA clips into {ORGANIZED_DIR}")


def print_summary():
    print("\n--- Dataset summary ---")
    if not os.path.exists(ORGANIZED_DIR):
        print("No organized data found.")
        return
    for class_name in sorted(os.listdir(ORGANIZED_DIR)):
        class_dir = os.path.join(ORGANIZED_DIR, class_name)
        if os.path.isdir(class_dir):
            n_files = len([f for f in os.listdir(class_dir) if f.lower().endswith(".wav")])
            print(f"  {class_name}: {n_files} clips")

    print("\nNOTE: 'scream_distress' class is NOT populated by this script.")
    print("Neither ESC-50 nor SESA contain a scream class. You need to either:")
    print("  1. Record team members screaming (15-20 clips, ~20 min effort)")
    print("  2. Pull scream clips from Freesound.org manually")
    print("  3. Use a Kaggle scream dataset (search 'scream detection kaggle')")
    print("Put resulting clips in: data/organized/scream_distress/")


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(ORGANIZED_DIR, exist_ok=True)

    # ESC-50
    esc50_zip = os.path.join(RAW_DIR, "esc50.zip")
    download_file(ESC50_ZIP_URL, esc50_zip)
    extract_zip(esc50_zip, RAW_DIR)
    organize_esc50()

    # SESA
    sesa_zip = os.path.join(RAW_DIR, "sesa.zip")
    download_file(SESA_ZIP_URL, sesa_zip)
    extract_zip(sesa_zip, os.path.join(RAW_DIR, "SESA"))
    organize_sesa()

    print_summary()


if __name__ == "__main__":
    main()
