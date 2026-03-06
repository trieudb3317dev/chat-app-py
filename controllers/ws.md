# WebSocket API (controllers/ws.py)

This file documents WebSocket endpoints used by the backend chat service.

Endpoints

1) `/ws/test` (WebSocket)
   - Purpose: simple test endpoint to validate WebSocket handshake and round-trip.
   - Behavior (server): accepts websocket handshake, reads one JSON message from client, responds with JSON containing `received_data`, then closes the socket.
   - Example client (browser JS):
     ```js
     const ws = new WebSocket('ws://localhost:8000/ws/test');
     ws.addEventListener('open', () => {
       ws.send(JSON.stringify({ hello: 'world' }));
     });
     ws.addEventListener('message', (e) => {
       console.log('server:', JSON.parse(e.data));
     });
     ws.addEventListener('close', () => console.log('closed'));
     ```

2) `/ws/{user_id}` (WebSocket)
   - Purpose: main chat socket for a user. Clients connect providing their user id.
   - Example URL: `ws://localhost:8000/ws/42` (where `42` is the user's id)
   - Server behavior: the server accepts the websocket and then listens for JSON messages. It uses a WebSocket manager to keep connections and to send messages from server-side code.

Message protocol (client -> server)
- All messages are JSON. The server expects an `action` key for many operations. Examples:
  - Mark a chat as seen:
    ```json
    {"action": "mark_seen", "chat_id": 123}
    ```
  - Send a chat message (if server supports it):
    ```json
    {"action": "send_message", "chat_id": 123, "content": "Hi"}
    ```

Message protocol (server -> client)
- Server sends JSON objects with a `type` field, e.g.:
  - `{ "type": "message_seen", "chat_id": 123, "by": 42 }`
  - `{ "type": "unread_count", "count": 3 }`
  - `{ "type": "new_message", "payload": { ... } }`

Client-side usage tips
- Use `WebSocket` in browser or a more featured wrapper that supports reconnects and heartbeats (see `useChatWebSocket` hook example earlier).
- WebSocket auth: browsers cannot set arbitrary request headers on the websocket handshake. Common approaches:
  - Use cookie-based session/auth (recommended): server issues auth cookies during login and they are sent automatically during the websocket handshake.
  - Short-lived token via query param (less secure): `ws://.../ws/42?token=abc` — validate server-side.

Testing
- The `/ws/test` endpoint is useful to verify the server accepts WebSocket handshakes and echos the data.
- Use `wscat` or `websocat` to test quickly:
  ```bash
  # wscat (npm):
  wscat -c ws://localhost:8000/ws/test
  > {"foo":"bar"}
  # should receive JSON reply with received_data
  ```

Notes for frontend engineers
- Ensure the backend is running on `ws://` (dev) or `wss://` (prod) and the origin/cors and cookie settings are configured correctly so the websocket handshake succeeds.
- If your client sees the error `ASGI callable returned without sending handshake`, it means the server route returned without calling `accept()`; the server code already fixes this for `/ws/test` and uses a manager that calls `accept()` for `/ws/{user_id}`.
