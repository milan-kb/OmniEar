"""
Organize the 3 manually-downloaded scream datasets into data/organized/.

scream1 (audio-dataset-of-scream-and-non-scream):
    Converted_Separately/scream/*.wav       -> scream_distress
    Converted_Separately/non_scream/*.wav   -> background

scream2 (human-screaming-detection-dataset):
    Screaming/*.wav       -> scream_distress
    NotScreaming/*.wav    -> background

scream3 (scream-dataset):
    flat + nested folder, .wav/.ogg/.aiff, scream-only (no negative class)
    -> all go to scream_distress

NIGENS (official general sound-events corpus):
    NIGENS_selected/NIGENS/{femaleScream,maleScream}/*.wav
    -> scream_distress

Non-WAV files (.ogg, .aiff) are converted to .wav using soundfile/librosa
so the rest of the pipeline (which expects WAV) can use them directly.

Run from project root: python organize_screams.py
Requires: pip install soundfile librosa
"""

import os
import shutil

try:
    import soundfile as sf
except ImportError:
    print("ERROR: soundfile not installed. Run: pip install soundfile librosa")
    raise

RAW_DIR = "data/_raw"
ORGANIZED_DIR = "data/organized"

AUDIO_EXTS = (".wav", ".ogg", ".aiff", ".aif", ".flac", ".mp3")


def convert_and_copy(src_path, dest_path):
    """Copy WAV as-is, or convert other formats to WAV."""
    ext = os.path.splitext(src_path)[1].lower()
    if ext == ".wav":
        shutil.copy2(src_path, dest_path)
    else:
        try:
            data, samplerate = sf.read(src_path)
            sf.write(dest_path, data, samplerate)
        except Exception as e:
            print(f"  Failed to convert {src_path}: {e}")
            return False
    return True


def organize_folder(src_folder, target_class, prefix):
    if not os.path.exists(src_folder):
        print(f"  Folder not found, skipping: {src_folder}")
        return 0

    dest_dir = os.path.join(ORGANIZED_DIR, target_class)
    os.makedirs(dest_dir, exist_ok=True)

    count = 0
    for root, _, files in os.walk(src_folder):
        for fname in files:
            if not fname.lower().endswith(AUDIO_EXTS):
                continue
            src = os.path.join(root, fname)
            base_name = os.path.splitext(fname)[0]
            dest_fname = f"{prefix}_{base_name}.wav"
            dest = os.path.join(dest_dir, dest_fname)
            if os.path.exists(dest):
                continue  # already done, skip
            if convert_and_copy(src, dest):
                count += 1
    return count


def print_summary():
    print("\n--- Full dataset summary ---")
    total = 0
    for class_name in sorted(os.listdir(ORGANIZED_DIR)):
        class_dir = os.path.join(ORGANIZED_DIR, class_name)
        if os.path.isdir(class_dir):
            n_files = len([f for f in os.listdir(class_dir) if f.lower().endswith(".wav")])
            print(f"  {class_name}: {n_files} clips")
            total += n_files
    print(f"  TOTAL: {total} clips")


def main():
    print("Organizing scream1 (scream / non_scream)...")
    n1 = organize_folder("data/_raw/scream1/Converted_Separately/scream", "scream_distress", "s1")
    n2 = organize_folder("data/_raw/scream1/Converted_Separately/non_scream", "background", "s1")
    print(f"  scream: +{n1}, non_scream: +{n2}")

    print("Organizing scream2 (Screaming / NotScreaming)...")
    n3 = organize_folder("data/_raw/scream2/Screaming", "scream_distress", "s2")
    n4 = organize_folder("data/_raw/scream2/NotScreaming", "background", "s2")
    print(f"  Screaming: +{n3}, NotScreaming: +{n4}")

    print("Organizing scream3 (scream-only, mixed formats)...")
    n5 = organize_folder("data/_raw/scream3", "scream_distress", "s3")
    print(f"  scream3: +{n5} (converted where needed)")

    print("Organizing NIGENS female/male scream classes...")
    n6 = organize_folder(
        "data/_raw/NIGENS_selected/NIGENS/femaleScream",
        "scream_distress",
        "nigens_f",
    )
    n7 = organize_folder(
        "data/_raw/NIGENS_selected/NIGENS/maleScream",
        "scream_distress",
        "nigens_m",
    )
    print(f"  NIGENS female: +{n6}, male: +{n7}")

    print_summary()


if __name__ == "__main__":
    main()
