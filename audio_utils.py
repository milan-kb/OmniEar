"""Shared audio feature utilities used by training and live inference.

Keeping these functions in one dependency-light module prevents subtle
training/inference drift.  In particular, both paths must select the same
event window and pool YAMNet frames in the same way.
"""

import numpy as np


# Older augmented files use names such as ``aug_pitch_up_clip.wav``.  Splitting
# on underscores is ambiguous because the technique names also contain
# underscores, so list the prefixes explicitly.
AUGMENTATION_PREFIXES = (
    "aug_pitch_up_",
    "aug_pitch_down_",
    "aug_stretch_fast_",
    "aug_stretch_slow_",
    "aug_noise_",
    "aug_gain_",
    "aug_playback_",
    "aug_room_",
    "aug_background_",
)


def get_group_id(filename):
    """Return the original clip name for a file or one of its augmentations."""
    for prefix in AUGMENTATION_PREFIXES:
        if filename.startswith(prefix):
            return filename[len(prefix):]

    # New/custom augmentations can use an unambiguous double-underscore form:
    # aug__technique_name__original.wav
    if filename.startswith("aug__"):
        parts = filename.split("__", 2)
        if len(parts) == 3 and parts[2]:
            return parts[2]

    return filename


def extract_loudest_window(waveform, window_samples, sample_rate):
    """Return a fixed-size slice centred on the highest-energy region."""
    waveform = np.asarray(waveform, dtype=np.float32).reshape(-1)
    if len(waveform) <= window_samples:
        pad = window_samples - len(waveform)
        return np.pad(waveform, (pad // 2, pad - pad // 2), mode="constant")

    frame_size = max(1, sample_rate // 10)
    n_frames = len(waveform) // frame_size
    frames = waveform[:n_frames * frame_size].reshape(n_frames, frame_size)
    frame_energies = np.sqrt(np.mean(np.square(frames, dtype=np.float64), axis=1))

    window_frames = max(1, window_samples // frame_size)
    if n_frames <= window_frames:
        center_frame = n_frames // 2
    else:
        cumsum = np.cumsum(np.insert(frame_energies, 0, 0.0))
        window_sums = cumsum[window_frames:] - cumsum[:-window_frames]
        center_frame = int(np.argmax(window_sums)) + window_frames // 2

    center_sample = center_frame * frame_size
    start = max(0, center_sample - window_samples // 2)
    start = min(start, len(waveform) - window_samples)
    return waveform[start:start + window_samples]


def pool_embedding_frames(embeddings, output_dim=None):
    """Pool YAMNet's time frames into one clip feature vector.

    The improved representation concatenates mean, max, and standard-deviation
    pooling.  Mean preserves the original clip context, max preserves a brief
    scream/impact that would otherwise be diluted by silence, and std captures
    temporal change.  ``output_dim`` keeps old 1024-input classifier files
    compatible until the user retrains the new 3072-input head.
    """
    frames = np.asarray(embeddings, dtype=np.float32)
    if frames.ndim != 2 or frames.shape[0] == 0:
        raise ValueError(f"Expected non-empty [frames, features] embeddings, got {frames.shape}")

    mean = np.mean(frames, axis=0)
    if output_dim is None:
        return np.concatenate(
            [mean, np.max(frames, axis=0), np.std(frames, axis=0)], axis=0
        ).astype(np.float32, copy=False)

    if output_dim == frames.shape[1]:
        return mean.astype(np.float32, copy=False)
    if output_dim == frames.shape[1] * 3:
        return np.concatenate(
            [mean, np.max(frames, axis=0), np.std(frames, axis=0)], axis=0
        ).astype(np.float32, copy=False)

    raise ValueError(
        f"Classifier expects {output_dim} features, but YAMNet provides "
        f"{frames.shape[1]} (legacy) or {frames.shape[1] * 3} (improved pooling)."
    )
