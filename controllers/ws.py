from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services import ws_service
from services import chat_service
from typing import Dict

router = APIRouter()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for a user. Clients should connect providing their
    user id in the path. Server pushes events like `new_message`,
    `message_seen`, `message_sent`, and `unread_count`.
    """
    await ws_service.manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            # simple protocol: expect {"action": "mark_seen", "chat_id": 123}
            action = data.get("action")
            if action == "mark_seen":
                if chat_id := data.get("chat_id"):
                    if updated := chat_service.mark_chat_as_seen(chat_id):
                        sender_id = updated.user_from_id
                        ws_service.manager.send_personal_sync(
                            sender_id,
                            {
                                "type": "message_seen",
                                "chat_id": updated.id,
                                "by": user_id,
                            },
                        )
                        # update unread count for recipient
                        unread = chat_service.count_unread_chats_for_user(sender_id)
                        ws_service.manager.send_personal_sync(
                            sender_id, {"type": "unread_count", "count": unread}
                        )
                                    # ping/pong or other messages can be handled here
    except WebSocketDisconnect:
        ws_service.manager.disconnect(websocket, user_id)
    except Exception:
        ws_service.manager.disconnect(websocket, user_id)
        raise
