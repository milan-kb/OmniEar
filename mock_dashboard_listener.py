"""OmniEar WebSocket relay and console monitor.

Both the edge pipeline and browser dashboard connect as WebSocket clients.
This process accepts the pipeline's alert, prints it, and broadcasts it to
every other connected client so the dashboard receives the same JSON frame.

Run this first, then start the frontend and ``omniear_pipeline.py``.
"""

import asyncio
import websockets
import json

HOST = "localhost"
PORT = 8765
CLIENTS = set()


async def broadcast(message, sender):
    recipients = [client for client in CLIENTS if client is not sender]
    if not recipients:
        print("[Relay] No dashboard client connected; alert printed only.")
        return

    results = await asyncio.gather(
        *(client.send(message) for client in recipients),
        return_exceptions=True,
    )
    delivered = sum(not isinstance(result, Exception) for result in results)
    print(f"[Relay] Forwarded alert to {delivered}/{len(recipients)} client(s).")


async def handler(websocket):
    CLIENTS.add(websocket)
    print(f"[Relay] Client connected: {websocket.remote_address} ({len(CLIENTS)} total)")
    try:
        async for message in websocket:
            try:
                alert = json.loads(message)
                if not isinstance(alert, dict):
                    print(f"[Relay] Ignored non-object JSON message: {message}")
                    continue
                print("\n[Relay] Received alert:")
                print(f"  Node: {alert.get('node_id')}")
                print(f"  Class: {alert.get('class')}  Label: {alert.get('label')}")
                print(f"  Confidence: {alert.get('confidence')}")
                print(f"  Location: ({alert.get('lat')}, {alert.get('lng')})")
                print(f"  Time: {alert.get('timestamp')}")
                await broadcast(message, websocket)
            except json.JSONDecodeError:
                print(f"[Relay] Ignored non-JSON message: {message}")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        CLIENTS.discard(websocket)
        print(f"[Relay] Client disconnected ({len(CLIENTS)} remaining).")


async def main():
    print(f"OmniEar relay listening on ws://{HOST}:{PORT}")
    print("Waiting for the pipeline and dashboard to connect...\n")
    async with websockets.serve(handler, HOST, PORT):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
