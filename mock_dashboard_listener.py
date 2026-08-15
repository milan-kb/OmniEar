"""
Mock WebSocket listener -- stands in for person1's dashboard so we can
test the alert sender end-to-end without waiting for his server.

Run this in one terminal: python mock_dashboard_listener.py
Then run omniear_pipeline.py in another terminal and trigger some sounds.
You should see alerts printed here as they arrive.
"""

import asyncio
import websockets
import json

HOST = "localhost"
PORT = 8765


async def handler(websocket):
    print(f"[Dashboard] Client connected: {websocket.remote_address}")
    try:
        async for message in websocket:
            try:
                alert = json.loads(message)
                print(f"\n[Dashboard] Received alert:")
                print(f"  Node: {alert.get('node_id')}")
                print(f"  Class: {alert.get('class')}  Label: {alert.get('label')}")
                print(f"  Confidence: {alert.get('confidence')}")
                print(f"  Location: ({alert.get('lat')}, {alert.get('lng')})")
                print(f"  Time: {alert.get('timestamp')}")
            except json.JSONDecodeError:
                print(f"[Dashboard] Received non-JSON message: {message}")
    except websockets.exceptions.ConnectionClosed:
        print("[Dashboard] Client disconnected.")


async def main():
    print(f"Mock dashboard listening on ws://{HOST}:{PORT}")
    print("Waiting for OmniEar pipeline to connect...\n")
    async with websockets.serve(handler, HOST, PORT):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
