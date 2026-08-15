"""
Guided Stage 1 test -- tells you exactly when to be quiet vs. make noise,
so we can unambiguously check trigger accuracy.

Run: python test_stage1_guided.py
"""

import time
import threading
from stage1_trigger import Stage1Trigger

trigger_log = []


def on_trigger(energy, timestamp):
    trigger_log.append((energy, timestamp))
    print(f"  >>> TRIGGERED (energy={energy:.4f})")


def run_phase(label, duration):
    print(f"\n=== {label} for {duration}s ===")
    for i in range(duration, 0, -1):
        print(f"  {i}...", end=" ", flush=True)
        time.sleep(1)
    print()


def main():
    trig = Stage1Trigger(on_trigger=on_trigger)

    # Start the stream in a background thread
    import sounddevice as sd
    stream = sd.InputStream(
        samplerate=16000,
        channels=1,
        blocksize=1600,
        callback=trig._audio_callback,
    )
    stream.start()

    print("Calibrating (stay silent)...")
    time.sleep(3)

    run_phase("PHASE 1: Stay SILENT", 5)
    silent_triggers = len(trigger_log)

    run_phase("PHASE 2: Talk NORMALLY (say something)", 5)
    talk_triggers = len(trigger_log) - silent_triggers

    print("\n=== PHASE 3: CLAP LOUDLY ONCE NOW ===")
    time.sleep(2)
    clap_triggers_before = len(trigger_log)
    time.sleep(2)
    clap_triggers = len(trigger_log) - clap_triggers_before

    stream.stop()
    stream.close()

    print("\n\n--- RESULTS ---")
    print(f"Triggers during SILENCE: {silent_triggers}  (want: 0)")
    print(f"Triggers during NORMAL TALK: {talk_triggers}  (want: 0, or low)")
    print(f"Triggers during CLAP: {clap_triggers}  (want: >=1)")
    print(f"\nAll trigger energies logged: {[round(e, 4) for e, t in trigger_log]}")


if __name__ == "__main__":
    main()
