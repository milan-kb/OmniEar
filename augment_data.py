"""
Data augmentation for threat classes.

Generates variants of existing clips via:
- Pitch shift (+/- semitones)
- Time stretch (slightly faster/slower)
- Relative-level background noise
- Speaker/streaming bandwidth loss
- Simple room echo

This multiplies effective training data for underrepresented classes
without needing new raw recordings. Augmented files are saved alongside
originals in the same class folders with an "aug_" prefix, so the
existing extract_embeddings.py picks them up automatically on next run.

Run: python augment_data.py
"""

import os
import numpy as np
import soundfile as sf
import librosa

ORGANIZED_DIR = "data/organized"
TARGET_SR = 16000

# Use broader shape changes for the data-poor classes. Screams already have
# more source clips, so add only the demo-domain transforms that simulate the
# YouTube -> speaker -> room -> microphone path.
AUGMENT_CONFIG = {
    "background": ("noise", "playback", "room"),
    "scream_distress": ("noise", "playback", "room"),
    "explosion": (
        "pitch_up", "pitch_down", "stretch_fast", "stretch_slow",
        "noise", "playback", "room",
    ),
    "impact_crash": (
        "pitch_up", "pitch_down", "stretch_fast", "stretch_slow",
        "noise", "playback", "room",
    ),
    "siren_traffic": (
        "pitch_up", "pitch_down", "stretch_fast", "stretch_slow",
        "noise", "playback", "room",
    ),
}


def load_audio(path):
    data, sr = sf.read(path, always_2d=False)
    if data.ndim > 1:
        data = np.mean(data, axis=1)
    data = data.astype(np.float32)
    if sr != TARGET_SR:
        data = librosa.resample(data, orig_sr=sr, target_sr=TARGET_SR)
    return data


def pitch_shift_variant(audio, n_steps):
    return librosa.effects.pitch_shift(audio, sr=TARGET_SR, n_steps=n_steps)


def time_stretch_variant(audio, rate):
    return librosa.effects.time_stretch(audio, rate=rate)


def _safe_peak(audio):
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    return (audio / max(peak, 1.0)).astype(np.float32, copy=False)


def add_noise_variant(audio, rng, snr_db=14.0):
    """Add noise relative to clip loudness instead of at a fixed amplitude."""
    signal_rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    noise_rms = max(signal_rms, 1e-4) / (10.0 ** (snr_db / 20.0))
    noise = rng.normal(0.0, noise_rms, len(audio)).astype(np.float32)
    return _safe_peak(audio + noise)


def playback_variant(audio):
    """Approximate bandwidth loss from YouTube -> laptop/phone speaker -> mic."""
    narrow = librosa.resample(audio, orig_sr=TARGET_SR, target_sr=8000)
    restored = librosa.resample(narrow, orig_sr=8000, target_sr=TARGET_SR)
    if len(restored) < len(audio):
        restored = np.pad(restored, (0, len(audio) - len(restored)))
    return _safe_peak(restored[:len(audio)] * 0.80)


def room_variant(audio):
    """Add two quiet echoes to simulate playback in a demo room."""
    output = audio.astype(np.float32, copy=True)
    for delay_seconds, gain in ((0.045, 0.28), (0.105, 0.14)):
        delay = int(TARGET_SR * delay_seconds)
        if len(output) > delay:
            output[delay:] += gain * audio[:-delay]
    return _safe_peak(output)


def generate_variants(audio, requested_techniques, rng):
    """Generate the requested augmented versions of one source clip."""
    variants = []
    techniques = {
        "pitch_up": lambda a: pitch_shift_variant(a, n_steps=2),
        "pitch_down": lambda a: pitch_shift_variant(a, n_steps=-2),
        "stretch_fast": lambda a: time_stretch_variant(a, rate=1.15),
        "stretch_slow": lambda a: time_stretch_variant(a, rate=0.85),
        "noise": lambda a: add_noise_variant(a, rng=rng, snr_db=14.0),
        "playback": playback_variant,
        "room": room_variant,
    }
    for name in requested_techniques:
        fn = techniques[name]
        try:
            variant = fn(audio.copy())
            variants.append((name, variant))
        except Exception as e:
            print(f"    Skipped {name}: {e}")
    return variants


def main():
    rng = np.random.default_rng(42)
    for class_name, requested_techniques in AUGMENT_CONFIG.items():
        class_dir = os.path.join(ORGANIZED_DIR, class_name)
        if not os.path.exists(class_dir):
            print(f"Class dir not found: {class_dir}, skipping.")
            continue

        original_files = [
            f for f in os.listdir(class_dir)
            if f.lower().endswith(".wav") and not f.startswith("aug_")
        ]
        print(
            f"\n[{class_name}] {len(original_files)} originals, generating "
            f"{len(requested_techniques)} variants each..."
        )

        generated = 0
        for i, fname in enumerate(original_files):
            path = os.path.join(class_dir, fname)
            base_name = os.path.splitext(fname)[0]
            missing_techniques = [
                technique
                for technique in requested_techniques
                if not os.path.exists(
                    os.path.join(class_dir, f"aug_{technique}_{base_name}.wav")
                )
            ]
            if not missing_techniques:
                continue
            try:
                audio = load_audio(path)
            except Exception as e:
                print(f"  Failed to load {fname}: {e}")
                continue

            variants = generate_variants(audio, missing_techniques, rng)

            for technique_name, variant_audio in variants:
                out_fname = f"aug_{technique_name}_{base_name}.wav"
                out_path = os.path.join(class_dir, out_fname)
                if os.path.exists(out_path):
                    continue
                sf.write(out_path, variant_audio, TARGET_SR)
                generated += 1

            if (i + 1) % 50 == 0:
                print(f"    {i + 1}/{len(original_files)} originals processed...")

        print(f"[{class_name}] Generated {generated} augmented clips.")

    print("\nDone. Re-run extract_embeddings.py to pick up the new augmented files,")
    print("then re-run train_classifier.py to retrain with the expanded dataset.")


if __name__ == "__main__":
    main()
