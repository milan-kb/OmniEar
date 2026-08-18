"""
OmniEar full pipeline: Stage 1 (energy trigger) gates Stage 2
(YAMNet embedding + trained classifier), producing structured JSON alerts.

Flow:
    mic -> Stage 1 energy trigger -> capture ~2s audio window
        -> YAMNet embedding -> classifier -> JSON alert

Run: python omniear_pipeline.py
"""

import os
import math
# Suppress TensorFlow/absl/CUDA log noise before importing tensorflow.
# We run CPU-only intentionally (no GPU on this machine), so the CUDA
# "could not find drivers" messages are expected and not useful to show.
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # 0=all, 1=info, 2=warning, 3=error only
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # explicitly disable GPU lookup, silences cuInit errors

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="tensorflow_hub")

import time
import json
import collections
import threading
import queue
import asyncio
import numpy as np
import sounddevice as sd
import tensorflow as tf
import tensorflow_hub as hub
import websockets
import requests

from stage1_trigger import Stage1Trigger, SAMPLE_RATE

# ---- Config ----
# Must match WINDOW_SECONDS in extract_embeddings.py -- training and live
# inference need to see the same size of audio window, otherwise the
# classifier sees a different embedding distribution live than what it
# was trained on.
WINDOW_SECONDS = 2.5
WINDOW_SAMPLES = int(SAMPLE_RATE * WINDOW_SECONDS)
MODEL_PATH = "models/classifier.keras"
CLASSES_PATH = "models/classes.json"
NODE_ID = "AE-01"
DEMO_LAT = 12.9716              # hardcoded demo coordinates
DEMO_LNG = 77.5946
DASHBOARD_WS_URL = "ws://localhost:8765"  # change to person1's server when ready
PI_LED_URL = "http://10.214.188.69:5000/trigger"  # confirmed working with person2's Pi
PI_LED_ENABLED = True  # set False to disable Pi calls entirely if hardware isn't ready

# Priority mapping per PRD -- adjust class names if yours differ
PRIORITY_MAP = {
    "scream_distress": "P0",
    "explosion": "P0",
    "impact_crash": "P1",
    "siren_traffic": "P4",
    "background": None,  # never alert on background
}

# Minimum confidence required before we alert on a class. Set per-class based on
# validation performance -- classes with lower precision (more false positives)
# get a higher bar. Tune these after re-running eval; these are reasonable starting
# points from the confusion matrix (background was frequently misread as impact_crash
# and siren_traffic).
CONFIDENCE_THRESHOLDS = {
    "scream_distress": 0.55,   # high recall/precision already, keep bar low
    "explosion": 0.60,
    "impact_crash": 0.65,      # lowered from 0.75 -- live testing showed correct
                                # classifications consistently landing 0.65-0.74,
                                # getting needlessly suppressed
    "siren_traffic": 0.65,     # lowered from 0.70 for the same reason, pending
                                # live validation
}

# Set True temporarily while calibrating thresholds against your actual demo
# playback setup (phone speaker, room, distance). Just changes what gets
# printed -- does not affect whether alerts actually fire.
DEBUG_LOG_ALL_CONFIDENCES = True

# Rolling audio buffer so we can grab audio from just BEFORE the trigger fired too,
# not just after -- Stage 1 detects the spike, but the interesting audio often starts
# slightly earlier in the block.
BUFFER_SECONDS = 3.0
# Store NumPy blocks rather than 48,000 individual Python floats. This keeps
# the real-time audio callback allocation-light and avoids boxing every sample.
ring_buffer = collections.deque(maxlen=math.ceil(BUFFER_SECONDS / 0.1))
buffer_lock = threading.Lock()


def notify_pi_led(alert_dict):
    """Send the alert to the Pi's LED trigger endpoint. Runs in its own thread
    so a slow/unreachable Pi (bad wifi, server not started, wrong IP) never
    blocks or crashes the main pipeline -- this is a nice-to-have physical
    prop, not a critical path."""
    if not PI_LED_ENABLED:
        return
    try:
        requests.post(PI_LED_URL, json=alert_dict, timeout=1.5)
        print("[Pi] LED trigger sent.")
    except requests.exceptions.RequestException as e:
        print(f"[Pi] LED trigger failed ({e}), continuing without it.")


def load_classes():
    with open(CLASSES_PATH) as f:
        return json.load(f)


class DashboardConnection:
    """Maintains a persistent WebSocket connection to the dashboard, running
    in its own asyncio event loop on a background thread, so the audio
    callback (which must stay fast and synchronous) can just hand off
    alerts without blocking on network I/O."""

    def __init__(self, url):
        self.url = url
        self.loop = asyncio.new_event_loop()
        self.ws = None
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect_loop())

    async def _connect_loop(self):
        while True:
            try:
                async with websockets.connect(self.url) as ws:
                    self.ws = ws
                    print(f"[Dashboard] Connected to {self.url}")
                    await ws.wait_closed()
            except Exception as e:
                print(f"[Dashboard] Connection failed ({e}), retrying in 3s...")
            self.ws = None
            await asyncio.sleep(3)

    def send_alert(self, alert_dict):
        ws = self.ws  # snapshot to avoid a race between the None check and use
        if ws is None:
            print("[Dashboard] Not connected, alert NOT sent (printed locally only).")
            return
        message = json.dumps(alert_dict)
        future = asyncio.run_coroutine_threadsafe(self._safe_send(ws, message), self.loop)
        future.add_done_callback(self._log_send_result)

    async def _safe_send(self, ws, message):
        await ws.send(message)

    def _log_send_result(self, future):
        exc = future.exception()
        if exc is not None:
            print(f"[Dashboard] Send failed: {exc}")


def extract_loudest_window(waveform, window_samples):
    """
    Same logic as extract_embeddings.py's version -- pick the window_samples-long
    slice centered on the loudest region. Must stay in sync with that function
    so training and inference see comparably-processed audio.
    """
    if len(waveform) <= window_samples:
        pad = window_samples - len(waveform)
        pad_left = pad // 2
        pad_right = pad - pad_left
        return np.pad(waveform, (pad_left, pad_right), mode="constant")

    frame_size = SAMPLE_RATE // 10
    n_frames = len(waveform) // frame_size
    if n_frames == 0:
        return waveform[:window_samples]

    frames = waveform[:n_frames * frame_size].reshape(n_frames, frame_size)
    frame_energies = np.sqrt(np.mean(np.square(frames, dtype=np.float64), axis=1))

    window_frames = max(1, window_samples // frame_size)
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


def classify_audio(waveform, yamnet, classifier, classes):
    """Run YAMNet + classifier on a waveform, return (label, confidence).
    Raises on failure -- caller is responsible for catching, since a bad
    waveform (e.g. buffer underrun producing silence/NaNs) should not be
    allowed to crash the pipeline."""
    windowed = extract_loudest_window(waveform, WINDOW_SAMPLES)
    _, embeddings, _ = yamnet(windowed)
    # Keep the hot path in TensorFlow. Converting embeddings to NumPy and then
    # back to a tensor for model.predict adds copies and data-adapter overhead.
    clip_embedding = tf.reduce_mean(embeddings, axis=0, keepdims=True)
    probs = classifier(clip_embedding, training=False)[0]
    top_idx = int(tf.argmax(probs).numpy())
    return classes[top_idx], float(probs[top_idx].numpy())


def make_alert(label, confidence):
    priority = PRIORITY_MAP.get(label)
    if priority is None:
        return None  # background, no alert

    threshold = CONFIDENCE_THRESHOLDS.get(label, 0.5)
    if confidence < threshold:
        print(f"[Stage 2] {label} confidence {confidence:.3f} below threshold {threshold}, suppressing alert.")
        return None

    return {
        "node_id": NODE_ID,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "class": priority,
        "label": label,
        "confidence": round(confidence, 3),
        "lat": DEMO_LAT,
        "lng": DEMO_LNG,
    }


def main():
    tf.get_logger().setLevel("ERROR")

    print("Loading YAMNet...")
    yamnet = hub.load("https://tfhub.dev/google/yamnet/1")
    print("Loading classifier...")
    classifier = tf.keras.models.load_model(MODEL_PATH)
    classes = load_classes()
    print(f"Classes: {classes}\n")

    print(f"Connecting to dashboard at {DASHBOARD_WS_URL}...")
    dashboard = DashboardConnection(DASHBOARD_WS_URL)

    # Only the newest trigger matters. Bounding this queue prevents stale audio
    # from piling up when inference takes longer than the trigger interval.
    inference_queue = queue.Queue(maxsize=1)

    def audio_ring_callback(indata, frames, time_info, status):
        with buffer_lock:
            ring_buffer.append(indata[:, 0].copy())

    def on_trigger(energy, timestamp):
        # This runs on the PortAudio real-time thread -- must return FAST.
        # Snapshot the buffer and hand off to the inference worker thread;
        # do NOT run YAMNet/classifier here, that would block audio capture
        # and cause dropped frames / a stale Stage 1 baseline.
        with buffer_lock:
            blocks = tuple(ring_buffer)
        item = (blocks, energy, timestamp)
        try:
            inference_queue.put_nowait(item)
        except queue.Full:
            # Replace queued stale work with the latest acoustic event.
            try:
                inference_queue.get_nowait()
            except queue.Empty:
                pass
            inference_queue.put_nowait(item)

    def inference_worker():
        while True:
            blocks, energy, timestamp = inference_queue.get()
            waveform = (
                np.concatenate(blocks).astype(np.float32, copy=False)
                if blocks
                else np.empty(0, dtype=np.float32)
            )
            print(f"\n[Stage 1] Trigger fired (energy={energy:.4f}). Running Stage 2...")

            if len(waveform) < SAMPLE_RATE * 0.5:
                print("[Stage 2] Not enough audio buffered yet, skipping.")
                continue

            try:
                label, confidence = classify_audio(waveform, yamnet, classifier, classes)
            except Exception as e:
                print(f"[Stage 2] Classification failed ({e}), skipping this trigger.")
                continue

            print(f"[Stage 2] Classified as: {label} (confidence={confidence:.3f})")

            alert = make_alert(label, confidence)
            if alert:
                print(f"[ALERT] {json.dumps(alert)}")
                dashboard.send_alert(alert)
                threading.Thread(target=notify_pi_led, args=(alert,), daemon=True).start()
            else:
                print("[Stage 2] Classified as background, no alert generated.")

    threading.Thread(target=inference_worker, daemon=True).start()

    trigger = Stage1Trigger(on_trigger=on_trigger)

    # Single stream feeds both the ring buffer AND the Stage 1 trigger logic
    def combined_callback(indata, frames, time_info, status):
        audio_ring_callback(indata, frames, time_info, status)
        trigger._audio_callback(indata, frames, time_info, status)

    print("OmniEar pipeline running. Listening...")
    print("Press Ctrl+C to stop.\n")

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        blocksize=int(SAMPLE_RATE * 0.1),
        dtype="float32",
        callback=combined_callback,
    ):
        try:
            while True:
                sd.sleep(1000)
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
