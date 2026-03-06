"""Simple test script that simulates two websocket clients (user 1 and user 2)
to exercise the new send_message / join_chat behavior.

Usage:
  pip install websockets
  python scripts/test_ws_clients.py

This will connect two clients to the running backend at ws://localhost:8000/ws/<user_id>.
It will have user 2 join chat with user 1, then have user 1 send a message to user 2.
Observe printed messages to verify seen/unread logic.
"""
import asyncio
import json
import websockets


async def client_listener(name, ws):
    try:
        async for msg in ws:
            try:
                data = json.loads(msg)
            except Exception:
                data = msg
            print(f"[{name}] recv: {data}")
    except websockets.ConnectionClosed:
        print(f"[{name}] connection closed")


async def run_test():
    uri1 = "ws://localhost:8000/ws/1"
    uri2 = "ws://localhost:8000/ws/2"

    async with websockets.connect(uri1) as ws1, websockets.connect(uri2) as ws2:
        print("Both clients connected")

        # Start listeners
        t1 = asyncio.create_task(client_listener("user1", ws1))
        t2 = asyncio.create_task(client_listener("user2", ws2))

        # user2 joins chat with user1 (so messages from user1 will be marked seen)
        await ws2.send(json.dumps({"action": "join_chat", "chat_with": 1}))
        print("user2 sent join_chat")

        await asyncio.sleep(0.5)

        # user1 sends a message to user2
        await ws1.send(json.dumps({"action": "send_message", "to": 2, "text": "Hello from user1"}))
        print("user1 sent message")

        # wait a moment to receive server events
        await asyncio.sleep(1)

        # Now user2 leaves chat
        await ws2.send(json.dumps({"action": "leave_chat"}))
        print("user2 left chat")

        await asyncio.sleep(0.2)

        # user1 sends another message (this one should increase unread for user2)
        await ws1.send(json.dumps({"action": "send_message", "to": 2, "text": "Second message"}))
        print("user1 sent second message")

        await asyncio.sleep(1)

        # close connections
        await ws1.close()
        await ws2.close()

        # cancel listener tasks
        t1.cancel()
        t2.cancel()


if __name__ == "__main__":
    asyncio.run(run_test())
