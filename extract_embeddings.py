"""
OmniEar Stage 2, step 1: extract YAMNet embeddings for every audio clip
in data/organized/<class>/*.wav and cache them to disk as a single
numpy archive, so we only need to run this once (embedding extraction
is the slow part; training the classifier on top is fast).

Run: python extract_embeddings.py
Output: data/embeddings.npz  (X = embeddings, y = labels, classes = class names)
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="tensorflow_hub")

import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import soundfile as sf
import librosa

ORGANIZED_DIR = "data/organized"
OUTPUT_PATH = "data/embeddings.npz"
TARGET_SR = 16000  # YAMNet requires 16kHz mono


def load_audio_mono_16k(path):
    """Load an audio file, convert to mono float32 at 16kHz."""
    data, sr = sf.read(path, always_2d=False)
    if data.ndim > 1:
        data = np.mean(data, axis=1)  # downmix to mono
    data = data.astype(np.float32)
    if sr != TARGET_SR:
        data = librosa.resample(data, orig_sr=sr, target_sr=TARGET_SR)
    return data


def main():
    print("Loading YAMNet...")
    yamnet = hub.load("https://tfhub.dev/google/yamnet/1")
    print("YAMNet loaded.\n")

    classes = sorted(
        d for d in os.listdir(ORGANIZED_DIR)
        if os.path.isdir(os.path.join(ORGANIZED_DIR, d))
    )
    print(f"Classes found: {classes}\n")

    all_embeddings = []
    all_labels = []
    failed = []

    for class_idx, class_name in enumerate(classes):
        class_dir = os.path.join(ORGANIZED_DIR, class_name)
        files = [f for f in os.listdir(class_dir) if f.lower().endswith(".wav")]
        print(f"[{class_name}] processing {len(files)} files...")

        for i, fname in enumerate(files):
            path = os.path.join(class_dir, fname)
            try:
                waveform = load_audio_mono_16k(path)
                if len(waveform) < 1600:  # shorter than 0.1s, too short to be useful
                    failed.append((path, "too short"))
                    continue

                scores, embeddings, spectrogram = yamnet(waveform)
                # Average embeddings across all frames in the clip -> one vector per clip
                clip_embedding = np.mean(embeddings.numpy(), axis=0)

                all_embeddings.append(clip_embedding)
                all_labels.append(class_idx)

            except Exception as e:
                failed.append((path, str(e)))

            if (i + 1) % 200 == 0:
                print(f"    {i + 1}/{len(files)} done")

        print(f"[{class_name}] done.\n")

    X = np.array(all_embeddings)
    y = np.array(all_labels)

    print(f"Total embeddings extracted: {len(X)}")
    print(f"Embedding shape: {X.shape}")
    print(f"Failed files: {len(failed)}")
    if failed:
        print("First 10 failures:")
        for path, reason in failed[:10]:
            print(f"  {path}: {reason}")

    np.savez(OUTPUT_PATH, X=X, y=y, classes=np.array(classes))
    print(f"\nSaved embeddings to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
