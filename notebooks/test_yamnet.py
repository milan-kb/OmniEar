"""
Quick sanity check: load YAMNet from TF Hub and run inference
on a short sample audio clip to confirm the pipeline works end-to-end.
"""

import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import urllib.request
import scipy.io.wavfile as wavfile
import io

print("Loading YAMNet from TF Hub (this downloads ~15MB the first time)...")
yamnet_model = hub.load("https://tfhub.dev/google/yamnet/1")
print("YAMNet loaded successfully.")

# Load the class map so we can print human-readable labels
class_map_path = yamnet_model.class_map_path().numpy()
class_names = []
with tf.io.gfile.GFile(class_map_path) as f:
    next(f)  # skip header
    for line in f:
        class_names.append(line.strip().split(",")[2])

print(f"Loaded {len(class_names)} class labels.")

# Grab a short public domain wav sample to test with
sample_url = "https://storage.googleapis.com/audioset/miaow_16k.wav"
print(f"Downloading test clip: {sample_url}")
wav_bytes = urllib.request.urlopen(sample_url).read()

sample_rate, wav_data = wavfile.read(io.BytesIO(wav_bytes))
print(f"Sample rate: {sample_rate}, shape: {wav_data.shape}, dtype: {wav_data.dtype}")

# YAMNet expects float32 waveform in [-1, 1] at 16kHz
waveform = wav_data.astype(np.float32) / 32768.0

# Run inference
scores, embeddings, spectrogram = yamnet_model(waveform)
print(f"\nScores shape: {scores.shape}")
print(f"Embeddings shape: {embeddings.shape}")

# Get the top predicted class averaged over the clip
mean_scores = np.mean(scores, axis=0)
top_class = np.argmax(mean_scores)

print(f"\nTop predicted class: {class_names[top_class]}")
print(f"Confidence: {mean_scores[top_class]:.3f}")

print("\n--- Top 5 classes ---")
top5 = np.argsort(mean_scores)[::-1][:5]
for i in top5:
    print(f"{class_names[i]}: {mean_scores[i]:.3f}")

print("\nYAMNet pipeline test PASSED.")
