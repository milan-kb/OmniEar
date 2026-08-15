"""
Data augmentation for weak classes (explosion, impact_crash, siren_traffic).

Generates variants of existing clips via:
- Pitch shift (+/- semitones)
- Time stretch (slightly faster/slower)
- Added background noise (mild, simulates real-world conditions)

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

# Classes to augment and how many variants to generate per original clip.
# background and scream_distress already have plenty of data, skip them.
AUGMENT_CONFIG = {
    "explosion": 3,
    "impact_crash": 5,      # weakest class, most aggressive augmentation
    "siren_traffic": 3,
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


def add_noise_variant(audio, noise_level=0.005):
    noise = np.random.normal(0, noise_level, len(audio)).astype(np.float32)
    return audio + noise


def generate_variants(audio, n_variants):
    """Generate n_variants augmented versions using a mix of techniques."""
    variants = []
    techniques = [
        ("pitch_up", lambda a: pitch_shift_variant(a, n_steps=2)),
        ("pitch_down", lambda a: pitch_shift_variant(a, n_steps=-2)),
        ("stretch_fast", lambda a: time_stretch_variant(a, rate=1.15)),
        ("stretch_slow", lambda a: time_stretch_variant(a, rate=0.85)),
        ("noise", lambda a: add_noise_variant(a, noise_level=0.008)),
    ]
    # cycle through techniques to cover n_variants, repeating if needed
    for i in range(n_variants):
        name, fn = techniques[i % len(techniques)]
        try:
            variant = fn(audio.copy())
            variants.append((name, variant))
        except Exception as e:
            print(f"    Skipped {name}: {e}")
    return variants


def main():
    for class_name, n_variants in AUGMENT_CONFIG.items():
        class_dir = os.path.join(ORGANIZED_DIR, class_name)
        if not os.path.exists(class_dir):
            print(f"Class dir not found: {class_dir}, skipping.")
            continue

        original_files = [
            f for f in os.listdir(class_dir)
            if f.lower().endswith(".wav") and not f.startswith("aug_")
        ]
        print(f"\n[{class_name}] {len(original_files)} originals, generating {n_variants} variants each...")

        generated = 0
        for i, fname in enumerate(original_files):
            path = os.path.join(class_dir, fname)
            try:
                audio = load_audio(path)
            except Exception as e:
                print(f"  Failed to load {fname}: {e}")
                continue

            base_name = os.path.splitext(fname)[0]
            variants = generate_variants(audio, n_variants)

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
