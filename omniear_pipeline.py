"""
OmniEar full pipeline: Stage 1 (energy trigger) gates Stage 2
(YAMNet embedding + trained classifier), producing structured JSON alerts.

Flow:
    mic -> Stage 1 energy trigger -> capture ~2s audio window
        -> YAMNet embedding -> classifier -> JSON alert

Run: python omniear_pipeline.py
"""

import time
import json
import collections
import threading
import asyncio
import numpy as np
import sounddevice as sd
import tensorflow as tf
import tensorflow_hub as hub
import websockets

from stage1_trigger import Stage1Trigger, SAMPLE_RATE

# ---- Config ----
CAPTURE_SECONDS = 2.0          # how much audio to grab for Stage 2 once Stage 1 fires
MODEL_PATH = "models/classifier.keras"
CLASSES_PATH = "models/classes.json"
NODE_ID = "AE-01"
DEMO_LAT = 12.9716              # hardcoded demo coordinates
DEMO_LNG = 77.5946
DASHBOARD_WS_URL = "ws://localhost:8765"  # change to person1's server when ready

# Priority mapping per PRD -- adjust class names if yours differ
PRIORITY_MAP = {
    "scream_distress": "P0",
    "explosion": "P0",
    "impact_crash": "P1",
    "siren_traffic": "P4",
    "background": None,  # never alert on background
}

# Rolling audio buffer so we can grab audio from just BEFORE the trigger fired too,
# not just after -- Stage 1 detects the spike, but the interesting audio often starts
# slightly earlier in the block.
BUFFER_SECONDS = 3.0
ring_buffer = collections.deque(maxlen=int(SAMPLE_RATE * BUFFER_SECONDS))
buffer_lock = threading.Lock()


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
        if self.ws is None:
            print("[Dashboard] Not connected, alert NOT sent (printed locally only).")
            return
        message = json.dumps(alert_dict)
        asyncio.run_coroutine_threadsafe(self.ws.send(message), self.loop)


def classify_audio(waveform, yamnet, classifier, classes):
    """Run YAMNet + classifier on a waveform, return (label, confidence)."""
    scores, embeddings, spectrogram = yamnet(waveform)
    clip_embedding = np.mean(embeddings.numpy(), axis=0, keepdims=True)
    probs = classifier.predict(clip_embedding, verbose=0)[0]
    top_idx = int(np.argmax(probs))
    return classes[top_idx], float(probs[top_idx])


def make_alert(label, confidence):
    priority = PRIORITY_MAP.get(label)
    if priority is None:
        return None  # background, no alert
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
    print("Loading YAMNet...")
    yamnet = hub.load("https://tfhub.dev/google/yamnet/1")
    print("Loading classifier...")
    classifier = tf.keras.models.load_model(MODEL_PATH)
    classes = load_classes()
    print(f"Classes: {classes}\n")

    print(f"Connecting to dashboard at {DASHBOARD_WS_URL}...")
    dashboard = DashboardConnection(DASHBOARD_WS_URL)
    time.sleep(1)  # give the connection a moment to establish before we start

    def audio_ring_callback(indata, frames, time_info, status):
        with buffer_lock:
            ring_buffer.extend(indata[:, 0].copy())

    def on_trigger(energy, timestamp):
        print(f"\n[Stage 1] Trigger fired (energy={energy:.4f}). Running Stage 2...")

        # Grab the current ring buffer contents as our capture window
        with buffer_lock:
            waveform = np.array(ring_buffer, dtype=np.float32)

        if len(waveform) < SAMPLE_RATE * 0.5:
            print("[Stage 2] Not enough audio buffered yet, skipping.")
            return

        label, confidence = classify_audio(waveform, yamnet, classifier, classes)
        print(f"[Stage 2] Classified as: {label} (confidence={confidence:.3f})")

        alert = make_alert(label, confidence)
        if alert:
            print(f"[ALERT] {json.dumps(alert)}")
            dashboard.send_alert(alert)
        else:
            print("[Stage 2] Classified as background, no alert generated.")

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
        callback=combined_callback,
    ):
        try:
            while True:
                sd.sleep(1000)
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
