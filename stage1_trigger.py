"""
OmniEar Stage 1: lightweight always-on anomaly trigger.

Listens to the live mic, computes short-term RMS energy, and fires a
trigger event when energy spikes above a rolling baseline. This gates
Stage 2 (the heavier YAMNet-based classifier) -- Stage 2 only runs when
Stage 1 detects something worth looking at.

Run directly to test standalone: python stage1_trigger.py
"""

import numpy as np
import sounddevice as sd
import time
import collections

SAMPLE_RATE = 16000          # match YAMNet's expected input rate for later integration
BLOCK_DURATION = 0.1         # seconds per audio block analyzed
BLOCK_SIZE = int(SAMPLE_RATE * BLOCK_DURATION)

BASELINE_WINDOW = 50         # number of blocks (~5s) used to compute rolling baseline
THRESHOLD_MULTIPLIER = 6.0   # trigger fires when energy > baseline * this multiplier
MIN_ABSOLUTE_ENERGY = 0.02   # hard floor -- ignore anything below this regardless of baseline
MIN_BASELINE_BLOCKS = 20     # don't trigger until we've seen enough blocks to estimate baseline
COOLDOWN_SECONDS = 1.5       # minimum time between consecutive triggers, avoids spamming


class Stage1Trigger:
    def __init__(self, on_trigger=None, device=None):
        """
        on_trigger: callback function called as on_trigger(energy, timestamp)
                    when an anomaly is detected. If None, just prints.
        device: sounddevice input device index/name, or None for default mic.
        """
        self.on_trigger = on_trigger or self._default_trigger
        self.device = device
        self.energy_history = collections.deque(maxlen=BASELINE_WINDOW)
        self.energy_sum = 0.0
        self.last_trigger_time = 0
        self.block_count = 0

    def _default_trigger(self, energy, timestamp):
        print(f"[TRIGGER] energy={energy:.4f} at t={timestamp:.2f}s")

    def _compute_energy(self, audio_block):
        # RMS energy of the block
        samples = np.asarray(audio_block, dtype=np.float32)
        return float(np.sqrt(np.mean(np.square(samples))))

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"Audio status warning: {status}")

        audio_block = indata[:, 0]  # mono
        energy = self._compute_energy(audio_block)
        self.block_count += 1

        # Need enough history before we trust the baseline
        if len(self.energy_history) >= MIN_BASELINE_BLOCKS:
            baseline = self.energy_sum / len(self.energy_history)
            threshold = max(baseline * THRESHOLD_MULTIPLIER, MIN_ABSOLUTE_ENERGY)

            now = time.time()
            if energy > threshold and (now - self.last_trigger_time) > COOLDOWN_SECONDS:
                self.last_trigger_time = now
                self.on_trigger(energy, now)

        # Plain rolling baseline -- always record, deque maxlen handles the windowing.
        # Occasional loud blocks slightly nudging the baseline is fine and self-corrects
        # within BASELINE_WINDOW blocks; the MIN_ABSOLUTE_ENERGY floor above prevents
        # the degenerate case where baseline collapses toward zero.
        if len(self.energy_history) == self.energy_history.maxlen:
            self.energy_sum -= self.energy_history[0]
        self.energy_history.append(energy)
        self.energy_sum += energy

    def run(self, duration=None):
        """Start listening. Blocks until duration expires or KeyboardInterrupt."""
        print(f"Stage 1 listening on device={self.device or 'default'} ...")
        print(f"Sample rate: {SAMPLE_RATE} Hz, block size: {BLOCK_SIZE} samples ({BLOCK_DURATION}s)")
        print("Calibrating baseline for the first ~2 seconds, stay quiet...")
        print("Press Ctrl+C to stop.\n")

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            blocksize=BLOCK_SIZE,
            device=self.device,
            callback=self._audio_callback,
        ):
            try:
                if duration:
                    sd.sleep(int(duration * 1000))
                else:
                    while True:
                        sd.sleep(1000)
            except KeyboardInterrupt:
                print("\nStopped.")


if __name__ == "__main__":
    trigger = Stage1Trigger()
    trigger.run()
