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
   - Captures audio before and after the first trigger spike
   - YAMNet (pretrained on AudioSet/YouTube) extracts frame embeddings
   - Fuses the trained project classifier with explicit YAMNet threat labels
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

## Model performance and evaluation status

The current classifier was rebuilt from **1,541 distinct source recordings**
and **8,624 clips after augmentation**. The sources are ESC-50, SESA, and the
female/male scream classes from NIGENS. It uses 3,072-feature YAMNet
mean/max/standard-deviation pooling, which retains short transient sounds much
better than averaging every frame into one embedding.

The split is stratified by class and grouped by original recording, so an
original clip and all of its augmented variants can never appear in different
train/validation/test splits. On the 257 untouched original recordings in the
held-out test split, the complete live classification path measured:

- **Overall accuracy: 86.8%**
- **Macro F1: 0.843**
- **Threat-category accuracy: 90.4%**
- **Background recall: 83.8%**
- explosion recall: 87.8%
- impact_crash recall: 100.0%
- scream_distress recall: 83.3% (only 12 scream recordings were in this split)
- siren_traffic recall: 89.5%

These are leakage-free demo estimates, not production safety guarantees. The
scream test sample is especially small, so test the exact YouTube clips and
speaker/microphone setup before presenting.

## Setup

```bash
python3.12 -m venv venv
source venv/bin/activate.fish   # or venv/bin/activate on bash
pip install -r requirements.txt   # or see manual install list below
```

Manual installs if no requirements.txt:
```bash
pip install tensorflow tensorflow-hub numpy scipy sounddevice websockets requests
pip install soundfile librosa scikit-learn setuptools
```

## Running

**1. Rebuild the dataset (only needed once, or after adding new data):**
```bash
python download_datasets.py       # pulls ESC-50 + SESA
python organize_screams.py        # imports NIGENS/manual scream folders if present
python augment_data.py            # adds weak-class + speaker/room variants
```

For the scream class used by the checked-in model, download the official
[NIGENS archive](https://zenodo.org/records/2535878) and place its
`femaleScream` and `maleScream` folders under
`data/_raw/NIGENS_selected/NIGENS/` before running `organize_screams.py`.
The trained model is already included, so this large download is unnecessary
unless you want to rebuild it.

**2. Extract embeddings + train (only needed once, or after dataset changes):**
```bash
python extract_embeddings.py      # caches YAMNet embeddings -> data/embeddings.npz
python train_classifier.py        # trains classifier -> models/classifier.keras
```

**3. Run the full system:**
```bash
# Starts the relay, dashboard, and detector together:
./start_omniear.sh

# Or run each component manually:
# Terminal 1 - relay server (broker between pipeline and dashboard)
python relay_server.py

# Terminal 2 - the frontend dashboard
cd acoustic-insight-sentinel
npm install   # first time only
npm run dev

# Terminal 3 - the actual detection pipeline
python omniear_pipeline.py
```

Open the dashboard at the URL `npm run dev` prints (typically `http://localhost:5173`).
`relay_server.py` must be running first — both the pipeline and the browser
dashboard connect to it as WebSocket clients, and it broadcasts each alert
from the pipeline out to the dashboard.

### Reliable demo testing

- Let the microphone calibrate for 2-3 seconds before playing anything.
- Play one clean event at a time, with roughly a second of audio after the
  first spike; classification deliberately waits 1.25 seconds to capture it.
- Keep `DEBUG_LOG_ALL_CONFIDENCES = True` while selecting clips. The console
  shows the custom-head scores, direct YAMNet evidence, and final fused scores.
- Prefer clips whose main sound begins within the first second and continues
  for at least another second. Avoid compilations with music, narration, or
  several event types in the same 2.5-second window.
- Test through the exact laptop, speaker, volume, mic position, and room that
  will be used in the presentation. The new `playback` and `room` augmentations
  approximate this path, but a short rehearsal set from the actual setup is
  still the most useful validation data.

## Known limitations (honest, per PRD Section 10)

- False-positive rates are not validated against chaotic real-world Indian soundscapes (festival noise, street vendors, etc.).
- The smallest class has only 76 distinct scream recordings; augmentation
  improves speaker/room robustness but cannot replace genuinely diverse data.
- `impact_crash` and `scream_distress` are not production-grade; their held-out
  test supports are only 24 and 12 recordings respectively.
- Hardware (ESP32/Pi node, GSM, solar) is not implemented for this demo — the pipeline runs on a laptop as a stand-in for the edge node, per architectural discussion in the PRD.
- Dashboard is a real, working frontend (`acoustic-insight-sentinel/`, submodule) connected via `relay_server.py` — not a mock. Physical LED/hardware trigger integration with person2's Pi is still pending real-world IP exchange at the venue.

## Team

- Model / pipeline / ML: [you]
- Dashboard / frontend: [person1]
- Hardware: [person2]
- Pitch: [person3]
