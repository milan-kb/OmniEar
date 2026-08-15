"""
One-off fix: organize SESA clips using the correct nested folder path.
Run this from your project root: python fix_sesa.py
Does NOT re-download anything, just re-organizes from data/_raw/SESA/SESA/.
"""

import os
import shutil

RAW_DIR = "data/_raw"
ORGANIZED_DIR = "data/organized"

SESA_ROOT = os.path.join(RAW_DIR, "SESA", "SESA")

SESA_CLASS_MAP = {
    "gunshot": "impact_crash",
    "explosion": "explosion",
    "siren": "siren_traffic",
    "casual": "background",
}


def main():
    if not os.path.exists(SESA_ROOT):
        print(f"ERROR: {SESA_ROOT} not found. Check your extraction path.")
        return

    count = 0
    class_counts = {}

    for split in ["train", "test"]:
        split_dir = os.path.join(SESA_ROOT, split)
        if not os.path.exists(split_dir):
            print(f"Skipping missing split: {split_dir}")
            continue

        for fname in os.listdir(split_dir):
            if not fname.lower().endswith(".wav"):
                continue
            lower_name = fname.lower()
            matched_class = None
            for key, target in SESA_CLASS_MAP.items():
                if lower_name.startswith(key):
                    matched_class = target
                    break
            if matched_class is None:
                print(f"  No match for: {fname}")
                continue

            dest_dir = os.path.join(ORGANIZED_DIR, matched_class)
            os.makedirs(dest_dir, exist_ok=True)
            src = os.path.join(split_dir, fname)
            dest = os.path.join(dest_dir, f"sesa_{split}_{fname}")
            shutil.copy2(src, dest)
            count += 1
            class_counts[matched_class] = class_counts.get(matched_class, 0) + 1

    print(f"\nOrganized {count} SESA clips total.")
    for cls, n in sorted(class_counts.items()):
        print(f"  {cls}: +{n}")

    print("\n--- Full current summary ---")
    for class_name in sorted(os.listdir(ORGANIZED_DIR)):
        class_dir = os.path.join(ORGANIZED_DIR, class_name)
        if os.path.isdir(class_dir):
            n_files = len([f for f in os.listdir(class_dir) if f.lower().endswith(".wav")])
            print(f"  {class_name}: {n_files} clips")


if __name__ == "__main__":
    main()
