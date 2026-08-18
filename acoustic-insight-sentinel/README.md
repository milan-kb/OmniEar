# AcousticEdge Dashboard

The AcousticEdge frontend is the operations dashboard for OmniEar's edge-AI acoustic alert pipeline. It receives structured alert JSON over WebSocket; no audio is received, stored, or displayed.

## Requirements

- Node.js 20 or later
- npm 10 or later
- The repository-root `mock_dashboard_listener.py` relay for live alerts

## Setup

```bash
npm install
cp .env.example .env
npm run dev
```

For the live feed, start the relay from the repository root before the frontend:

```bash
python mock_dashboard_listener.py
```

The Python pipeline and browser are both WebSocket clients. The relay receives each pipeline
alert and broadcasts it to connected dashboards.

The local default WebSocket endpoint is `ws://localhost:8765`. Override it in `.env` when the pipeline is hosted elsewhere:

```env
VITE_WS_URL=ws://hostname:8765
```

## Commands

```bash
npm run dev
npm run build
npx tsc --noEmit
npm run lint
```

## Live alert contract

The dashboard accepts one JSON text frame per alert:

```json
{
  "node_id": "AE-01",
  "timestamp": "2026-08-16T09:12:03Z",
  "class": "P0",
  "label": "scream_distress",
  "confidence": 0.91,
  "lat": 12.9716,
  "lng": 77.5946
}
```

Malformed messages are logged and ignored. The operations feed and node-network map update live;
operators can open an incident, acknowledge it, and resolve it for the current browser session.
The operations feed also includes an explicitly labelled local test-alert button for demos without
a microphone or trained model running.
Fleet hardware information, the personal node, and Analytics' historical dB charts are clearly
labelled local demonstrations because the pipeline does not provide hardware telemetry, sound
level, or district aggregates.
