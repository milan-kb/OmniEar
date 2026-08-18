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
import csv
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

from audio_utils import extract_loudest_window, pool_embedding_frames
from stage1_trigger import Stage1Trigger, SAMPLE_RATE
from threat_fusion import (
    aggregate_yamnet_evidence,
    build_yamnet_index_groups,
    fuse_predictions,
)

# ---- Config ----
# Must match WINDOW_SECONDS in extract_embeddings.py -- training and live
# inference need to see the same size of audio window, otherwise the
# classifier sees a different embedding distribution live than what it
# was trained on.
WINDOW_SECONDS = 2.5
WINDOW_SAMPLES = int(SAMPLE_RATE * WINDOW_SECONDS)
# Stage 1 fires on the first loud 100ms block. Waiting here is essential: an
# immediate snapshot contains almost entirely audio from before the event.
POST_TRIGGER_SECONDS = 1.25
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
    # These conservative alert gates are based on the final model's untouched
    # background errors. Classification is still printed below the threshold,
    # but ambiguous results no longer become dashboard/Pi alerts.
    "scream_distress": 0.52,
    "explosion": 0.65,
    "impact_crash": 0.69,
    "siren_traffic": 0.80,
}

# Set True temporarily while calibrating thresholds against your actual demo
# playback setup (phone speaker, room, distance). Just changes what gets
# printed -- does not affect whether alerts actually fire.
DEBUG_LOG_ALL_CONFIDENCES = True

# Rolling audio buffer so we can grab audio from just BEFORE the trigger fired too,
# not just after -- Stage 1 detects the spike, but the interesting audio often starts
# slightly earlier in the block.
BUFFER_SECONDS = 3.5
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


def load_yamnet_class_names(yamnet):
    """Read the 521 display names bundled with the loaded TF Hub model."""
    class_map_path = yamnet.class_map_path().numpy()
    if isinstance(class_map_path, bytes):
        class_map_path = class_map_path.decode("utf-8")
    with tf.io.gfile.GFile(class_map_path) as class_map_file:
        reader = csv.reader(class_map_file)
        next(reader)
        return [row[2] for row in reader]


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


def _format_scores(values, classes, limit=5):
    top = np.argsort(values)[::-1][:limit]
    return ", ".join(f"{classes[i]}={float(values[i]):.3f}" for i in top)


def classify_audio(waveform, yamnet, classifier, classes, yamnet_index_groups=None):
    """Run YAMNet + classifier on a waveform, return (label, confidence).
    Raises on failure -- caller is responsible for catching, since a bad
    waveform (e.g. buffer underrun producing silence/NaNs) should not be
    allowed to crash the pipeline."""
    windowed = extract_loudest_window(waveform, WINDOW_SAMPLES, SAMPLE_RATE)
    yamnet_scores, embeddings, _ = yamnet(windowed)
    embedding_frames = embeddings.numpy()

    # New models use mean+max+std (3072 inputs), while the checked-in legacy
    # model uses mean only (1024). This lets the improved live path work now and
    # upgrades automatically after extract_embeddings.py + training are rerun.
    model_input_dim = int(classifier.input_shape[-1])
    clip_feature = pool_embedding_frames(embedding_frames, output_dim=model_input_dim)
    clip_probs = classifier(clip_feature[None, :], training=False)[0].numpy()

    # The legacy model can also score each 0.96s YAMNet frame. Top-two temporal
    # pooling stops a brief event from being averaged into background.
    frame_probs = None
    if model_input_dim == embedding_frames.shape[1]:
        frame_probs = classifier(embedding_frames, training=False).numpy()

    evidence = np.zeros(len(classes), dtype=np.float32)
    if yamnet_index_groups:
        evidence = aggregate_yamnet_evidence(
            yamnet_scores.numpy(), yamnet_index_groups, classes
        )

    probs, details = fuse_predictions(clip_probs, frame_probs, evidence, classes)
    top_idx = int(np.argmax(probs))

    if DEBUG_LOG_ALL_CONFIDENCES:
        print(f"[Debug] learned: {_format_scores(details['learned'], classes)}")
        if details["yamnet_weight"] > 0:
            print(
                f"[Debug] YAMNet evidence: "
                f"{_format_scores(details['yamnet_evidence'], classes, limit=4)} "
                f"(fusion weight={details['yamnet_weight']:.2f})"
            )
        print(f"[Debug] fused: {_format_scores(probs, classes)}")

    return classes[top_idx], float(probs[top_idx])


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
    classifier = tf.keras.models.load_model(MODEL_PATH, compile=False)
    classes = load_classes()
    try:
        yamnet_class_names = load_yamnet_class_names(yamnet)
        yamnet_index_groups = build_yamnet_index_groups(yamnet_class_names)
        mapped_count = sum(len(indices) for indices in yamnet_index_groups.values())
        print(f"Loaded {mapped_count} YAMNet threat-label mappings.")
    except Exception as exc:
        # The custom classifier remains fully usable if a future TF Hub export
        # changes how the class-map asset is exposed.
        yamnet_index_groups = {}
        print(f"Could not load YAMNet class map ({exc}); using custom classifier only.")
    print(f"Classes: {classes}\n")

    print(f"Connecting to dashboard at {DASHBOARD_WS_URL}...")
    dashboard = DashboardConnection(DASHBOARD_WS_URL)

    # Only the newest trigger matters. Bounding this queue prevents stale audio
    # from piling up when inference takes longer than the trigger interval.
    inference_queue = queue.Queue(maxsize=1)
    capture_state_lock = threading.Lock()
    capture_state = {"pending": False, "energy": 0.0, "timestamp": 0.0}

    def audio_ring_callback(indata, frames, time_info, status):
        with buffer_lock:
            ring_buffer.append(indata[:, 0].copy())

    def enqueue_latest(item):
        """Put an event on the bounded queue, replacing stale unprocessed work."""
        try:
            inference_queue.put_nowait(item)
            return
        except queue.Full:
            pass
        try:
            inference_queue.get_nowait()
        except queue.Empty:
            pass
        inference_queue.put_nowait(item)

    def finish_event_capture():
        # Called by a timer, never by PortAudio's real-time callback.
        with buffer_lock:
            blocks = tuple(ring_buffer)
        with capture_state_lock:
            energy = capture_state["energy"]
            timestamp = capture_state["timestamp"]
            capture_state["pending"] = False
        enqueue_latest((blocks, energy, timestamp))

    def on_trigger(energy, timestamp):
        # This runs on the PortAudio real-time thread and must return quickly.
        # Delay the snapshot so it contains the event after its first spike.
        with capture_state_lock:
            if capture_state["pending"]:
                capture_state["energy"] = max(capture_state["energy"], energy)
                return
            capture_state.update(pending=True, energy=energy, timestamp=timestamp)

        print(
            f"\n[Stage 1] Trigger fired (energy={energy:.4f}). "
            f"Capturing {POST_TRIGGER_SECONDS:.2f}s of event audio..."
        )
        capture_timer = threading.Timer(POST_TRIGGER_SECONDS, finish_event_capture)
        capture_timer.daemon = True
        capture_timer.start()

    def inference_worker():
        while True:
            blocks, energy, timestamp = inference_queue.get()
            waveform = (
                np.concatenate(blocks).astype(np.float32, copy=False)
                if blocks
                else np.empty(0, dtype=np.float32)
            )
            print(f"[Stage 2] Running classification (peak energy={energy:.4f})...")

            if len(waveform) < SAMPLE_RATE * 0.5:
                print("[Stage 2] Not enough audio buffered yet, skipping.")
                continue

            try:
                label, confidence = classify_audio(
                    waveform,
                    yamnet,
                    classifier,
                    classes,
                    yamnet_index_groups=yamnet_index_groups,
                )
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
                print("[Stage 2] No alert emitted.")

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
