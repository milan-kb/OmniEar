# OmniEar

Edge-AI acoustic threat detection — listens for distress/emergency sounds (screams, explosions, impacts, sirens) and generates structured alerts without ever recording or transmitting raw audio.

Built for [hackathon name] as a technical proof-of-concept demonstrating the core detection pipeline from AcousticEdge / OmniEar's PRD.

## Architecture

```
Mic (live audio)
   |
   v
Stage 1: Energy Threshold Trigger  (stage1_trigger.py)
   - Cheap, always-on RMS energy monitoring
   - Adaptive rolling baseline + absolute floor
   - Fires only when a real anomaly is detected
   |
   v
Stage 2: YAMNet + Trained Classifier  (omniear_pipeline.py)
   - Captures ~2-3s audio window around the trigger
   - YAMNet (pretrained, TF Hub) extracts embeddings
   - Small dense classifier (trained on our dataset) predicts class
   |
   v
JSON Alert  (matches PRD alert schema)
   {"node_id", "timestamp", "class" (P0/P1/P4), "label",
    "confidence", "lat", "lng"}
   |
   v
WebSocket -> Dashboard
```

**No raw audio ever leaves the device** — only the structured alert payload above.

## Classes detected

| Class | Priority | Notes |
|---|---|---|
| scream_distress | P0 | Covers assault, ragging, personal emergencies |
| explosion | P0 | |
| impact_crash | P1 | Glass breaking / gunshot / crash-adjacent transients |
| siren_traffic | P4 | Non-urgent, monitoring only |
| background | — | No alert generated |

## Current model performance (test set)

Trained on 10,138 clips (ESC-50, SESA, + augmented data for weak classes) using YAMNet embeddings + a small classifier head.

- **Overall accuracy: 89%**
- **Macro F1: 0.89**
- scream_distress: 88% precision / 89% recall
- explosion: 98% precision / 96% recall
- impact_crash: 75% precision / 98% recall
- siren_traffic: 86% precision / 87% recall
- background: 93% precision / 88% recall

Per-class confidence thresholds are applied before alerting (see `CONFIDENCE_THRESHOLDS` in `omniear_pipeline.py`) to further reduce false positives on weaker classes.

## Setup

```bash
python3.12 -m venv venv
source venv/bin/activate.fish   # or venv/bin/activate on bash
pip install -r requirements.txt   # or see manual install list below
```

Manual installs if no requirements.txt:
```bash
pip install tensorflow tensorflow-hub numpy scipy sounddevice websockets
pip install soundfile librosa scikit-learn setuptools
```

## Running

**1. Rebuild the dataset (only needed once, or after adding new data):**
```bash
python download_datasets.py       # pulls ESC-50 + SESA
python fix_sesa.py                # organizes SESA into class folders
python organize_screams.py        # organizes manually-downloaded scream datasets
python augment_data.py            # generates augmented variants for weak classes
```

**2. Extract embeddings + train (only needed once, or after dataset changes):**
```bash
python extract_embeddings.py      # caches YAMNet embeddings -> data/embeddings.npz
python train_classifier.py        # trains classifier -> models/classifier.keras
```

**3. Run the live pipeline:**
```bash
# Terminal 1 - mock dashboard (or point at the real one)
python mock_dashboard_listener.py

# Terminal 2 - the actual pipeline
python omniear_pipeline.py
```

## Known limitations (honest, per PRD Section 10)

- False-positive rates not yet validated against chaotic real-world Indian soundscapes (festival noise, street vendors, etc.) — validated only against clean dataset audio and live personal testing so far.
- `impact_crash` and `siren_traffic` classes have less training data than `background`/`scream_distress` even after augmentation; precision is improving but not yet production-grade.
- Hardware (ESP32/Pi node, GSM, solar) is not implemented for this demo — the pipeline runs on a laptop as a stand-in for the edge node, per architectural discussion in the PRD.
- Dashboard integration and physical LED/hardware trigger are built by teammates and integrate via the WebSocket JSON contract documented above.

## Team

- Model / pipeline / ML: [you]
- Dashboard / frontend: [person1]
- Hardware: [person2]
- Pitch: [person3]
