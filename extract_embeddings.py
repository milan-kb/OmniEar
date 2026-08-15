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

# Must match CAPTURE_SECONDS in omniear_pipeline.py -- training windows should
# match what the live pipeline actually captures, otherwise the classifier is
# trained on a different embedding distribution than what it sees at inference
# (e.g. averaging over a 33s clip vs. averaging over a 2-3s live capture).
WINDOW_SECONDS = 2.5
WINDOW_SAMPLES = int(TARGET_SR * WINDOW_SECONDS)


def load_audio_mono_16k(path):
    """Load an audio file, convert to mono float32 at 16kHz."""
    data, sr = sf.read(path, always_2d=False)
    if data.ndim > 1:
        data = np.mean(data, axis=1)  # downmix to mono
    data = data.astype(np.float32)
    if sr != TARGET_SR:
        data = librosa.resample(data, orig_sr=sr, target_sr=TARGET_SR)
    return data


def extract_loudest_window(waveform, window_samples):
    """
    Return a window_samples-long slice of the waveform centered on its
    loudest region. For clips shorter than the window, pad with zeros
    (silence) rather than stretching -- this matches what actually happens
    live when Stage 1 fires on a short sound and the ring buffer has less
    than a full window of real audio.
    """
    if len(waveform) <= window_samples:
        pad = window_samples - len(waveform)
        pad_left = pad // 2
        pad_right = pad - pad_left
        return np.pad(waveform, (pad_left, pad_right), mode="constant")

    # Find the loudest window via a coarse sliding RMS scan (frame-level,
    # not sample-level, for speed)
    frame_size = TARGET_SR // 10  # 0.1s frames
    n_frames = len(waveform) // frame_size
    if n_frames == 0:
        return waveform[:window_samples]

    frame_energies = np.array([
        np.sqrt(np.mean(waveform[i * frame_size:(i + 1) * frame_size].astype(np.float64) ** 2))
        for i in range(n_frames)
    ])

    window_frames = max(1, window_samples // frame_size)
    # Sliding sum of energies across window_frames-sized spans, find the loudest span
    if n_frames <= window_frames:
        center_frame = n_frames // 2
    else:
        cumsum = np.cumsum(np.insert(frame_energies, 0, 0))
        window_sums = cumsum[window_frames:] - cumsum[:-window_frames]
        best_start_frame = int(np.argmax(window_sums))
        center_frame = best_start_frame + window_frames // 2

    center_sample = center_frame * frame_size
    start = max(0, center_sample - window_samples // 2)
    end = start + window_samples
    if end > len(waveform):
        end = len(waveform)
        start = max(0, end - window_samples)

    windowed = waveform[start:end]
    if len(windowed) < window_samples:
        windowed = np.pad(windowed, (0, window_samples - len(windowed)), mode="constant")
    return windowed


def get_group_id(filename):
    """
    Return the identity of the ORIGINAL clip this file came from, so augmented
    variants (aug_pitch_up_X.wav, aug_noise_X.wav, etc.) are grouped with their
    source clip. This prevents a pitch-shifted copy of a training clip from
    leaking into the test set, which would inflate test metrics.
    """
    name = filename
    if name.startswith("aug_"):
        # aug_<technique>_<original_stem>.wav -> strip the aug_<technique>_ prefix
        parts = name.split("_", 2)
        if len(parts) == 3:
            name = parts[2]
    return name


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
    all_groups = []
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

                windowed = extract_loudest_window(waveform, WINDOW_SAMPLES)

                scores, embeddings, spectrogram = yamnet(windowed)
                # Average embeddings across the windowed clip -> one vector per clip.
                # This matches the ~2-3s live capture window used at inference time.
                clip_embedding = np.mean(embeddings.numpy(), axis=0)

                all_embeddings.append(clip_embedding)
                all_labels.append(class_idx)
                all_groups.append(f"{class_name}/{get_group_id(fname)}")

            except Exception as e:
                failed.append((path, str(e)))

            if (i + 1) % 200 == 0:
                print(f"    {i + 1}/{len(files)} done")

        print(f"[{class_name}] done.\n")

    X = np.array(all_embeddings)
    y = np.array(all_labels)
    groups = np.array(all_groups)

    print(f"Total embeddings extracted: {len(X)}")
    print(f"Embedding shape: {X.shape}")
    print(f"Unique groups (original clips): {len(set(all_groups))}")
    print(f"Failed files: {len(failed)}")
    if failed:
        print("First 10 failures:")
        for path, reason in failed[:10]:
            print(f"  {path}: {reason}")

    np.savez(OUTPUT_PATH, X=X, y=y, classes=np.array(classes), groups=groups)
    print(f"\nSaved embeddings to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
