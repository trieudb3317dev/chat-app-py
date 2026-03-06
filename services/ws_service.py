import asyncio
from typing import Dict, Set, Any, Optional
import traceback


class WebSocketManager:
    """Manage websocket connections keyed by user_id.

    For synchronous callers we provide `send_personal_sync` which schedules
    the send coroutine on the websocket's event loop using
    asyncio.run_coroutine_threadsafe.
    """

    def __init__(self):
        # user_id -> set of websocket connections
        self.connections: Dict[int, Set[Any]] = {}
        # websocket -> event loop that accepted it
        self._loops: Dict[Any, asyncio.AbstractEventLoop] = {}
        # websocket -> metadata (e.g., current chat the websocket is viewing)
        self._current_chat: Dict[Any, int] = {}

    async def connect(self, websocket, user_id: int):
        await websocket.accept()
        loop = asyncio.get_running_loop()
        self._loops[websocket] = loop
        conns = self.connections.setdefault(user_id, set())
        conns.add(websocket)
        # initialize metadata
        self._current_chat[websocket] = None

    def disconnect(self, websocket, user_id: int):
        try:
            conns = self.connections.get(user_id)
            if conns and websocket in conns:
                conns.remove(websocket)
                if not conns:
                    del self.connections[user_id]
        finally:
            self._loops.pop(websocket, None)
            self._current_chat.pop(websocket, None)

    async def send_personal(self, user_id: int, message: dict):
        """Async send: await this from async context."""
        conns = list(self.connections.get(user_id, []))
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                traceback.print_exc()

    def send_personal_sync(self, user_id: int, message: dict):
        """Sync-friendly send: schedules coroutine on each websocket's loop."""
        conns = list(self.connections.get(user_id, []))
        for ws in conns:
            loop = self._loops.get(ws)
            if loop and loop.is_running():
                coro = ws.send_json(message)
                try:
                    asyncio.run_coroutine_threadsafe(coro, loop)
                except Exception:
                    traceback.print_exc()

    def set_current_chat(self, websocket, chat_with_user_id: Optional[int]):
        """Set the 'current chat' context for a websocket connection.

        chat_with_user_id should be the other participant's user id (int) or None.
        Used to determine whether an incoming message should be marked seen or unread.
        """
        if websocket in self._current_chat:
            self._current_chat[websocket] = chat_with_user_id

    def get_current_chat(self, websocket):
        return self._current_chat.get(websocket)

    def user_is_viewing_chat(self, user_id: int, chat_with_user_id: int) -> bool:
        """Return True if any active websocket for `user_id` has current_chat == chat_with_user_id."""
        conns = list(self.connections.get(user_id, []))
        return any(self._current_chat.get(ws) == chat_with_user_id for ws in conns)

    async def broadcast(self, message: dict):
        for user_id in list(self.connections.keys()):
            await self.send_personal(user_id, message)


# global manager instance used by websocket endpoint and services
manager = WebSocketManager()
