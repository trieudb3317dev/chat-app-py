import contextlib
import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services import ws_service
from services import chat_service
from typing import Dict

router = APIRouter()


@router.websocket("/ws/test")
async def websocket_test(websocket: WebSocket, data: Dict = None):
    """Simple test endpoint to verify WebSocket functionality.

    This endpoint will accept the WebSocket handshake, send a single
    JSON message and then close the connection. Previously the handler
    returned a dict which caused the ASGI server to return without
    sending the handshake (error: "ASGI callable returned without
    sending handshake").
    """
    # Accept the websocket handshake so the client can establish the
    # websocket connection instead of the route returning early.
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        await websocket.send_json(
            {"message": "WebSocket endpoint is working!", "received_data": data}
        )
    finally:
        await websocket.close()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    # sourcery skip: low-code-quality
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
            # actions supported: join_chat, leave_chat, mark_seen, send_message
            if action == "join_chat":
                # client indicates it's viewing a chat with another user
                chat_with = data.get("chat_with")
                print(f"User {user_id} joined chat with {chat_with}")
                # chat_with should be the other participant's user id (int) or None
                ws_service.manager.set_current_chat(websocket, chat_with)

                # send recent history to the client who just joined the chat
                try:
                    history = chat_service.get_conversation_between_users(
                        user_id, chat_with, page=1, per_page=50
                    )
                    # service may return a paginated dict or a plain list
                    raw_messages = (
                        history.get("items", [])
                        if isinstance(history, dict)
                        else history
                    )
                    # ensure datetimes are JSON-serializable
                    def serialize_messages(items):
                        out = []
                        for m in items:
                            try:
                                # copy dict to avoid mutating service return
                                mm = dict(m)
                            except Exception:
                                mm = m
                            ca = mm.get("created_at")
                            if isinstance(ca, datetime.datetime):
                                mm["created_at"] = ca.isoformat()
                            out.append(mm)
                        return out

                    messages_payload = serialize_messages(raw_messages)

                    # send directly to the joining websocket (immediate)
                    await websocket.send_json(
                        {
                            "type": "history_update",
                            "chat_with": chat_with,
                            "messages": messages_payload,
                        }
                    )

                    # if the other participant is currently viewing this chat, push history to them as well
                    if chat_with is not None:
                        if recipient_viewing := ws_service.manager.user_is_viewing_chat(
                            chat_with, user_id
                        ):
                            ws_service.manager.send_personal_sync(
                                chat_with,
                                {
                                    "type": "history_update",
                                    "chat_with": chat_with,
                                    "messages": messages_payload,
                                },
                            )
                except Exception as e:
                    # log but don't break the websocket loop
                    print(f"Error sending history on join_chat: {e}")

            elif action == "leave_chat":
                ws_service.manager.set_current_chat(websocket, None)
                # send unread count update to the user who left the chat, so their client can decide what to do (e.g., show unread badge)
                unread = chat_service.count_unread_chats_for_user_and_group_by_sender(
                    user_id
                )
                ws_service.manager.send_personal_sync(
                    user_id, {"type": "unread_count", "count": unread}
                )

            elif action == "mark_seen":
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
                        # update unread count for sender
                        unread = chat_service.count_unread_chats_for_user_and_group_by_sender(sender_id)
                        ws_service.manager.send_personal_sync(
                            sender_id, {"type": "unread_count", "count": unread}
                        )

            elif action == "send_message":
                # expected payload: { action: 'send_message', to: <recipient_id>, text: '...' }
                to_id = data.get("to")
                text = data.get("text")
                if not to_id or text is None:
                    # ignore malformed
                    continue

                # determine whether recipient is currently viewing the chat with sender
                recipient_viewing = ws_service.manager.user_is_viewing_chat(
                    to_id, user_id
                )

                # create chat and notify; if recipient is viewing, mark as seen immediately
                chat = chat_service.create_chat(
                    user_to_id=to_id,
                    user_from_id=user_id,
                    text=text,
                    notify=True,
                    mark_seen=bool(recipient_viewing),
                )
                # optionally echo back to sender (ack)
                ws_service.manager.send_personal_sync(
                    user_id,
                    {
                        "type": "message_sent",
                        "chat_id": chat.id,
                        "to": to_id,
                        "text": chat.text,
                    },
                )
                # send history message to update chat view for sender (and recipient if they're viewing)
                try:
                    history = chat_service.get_conversation_between_users(
                        user_id, to_id, page=1, per_page=50
                    )
                    if isinstance(history, dict):
                        raw_messages = history.get("items", [])
                    else:
                        raw_messages = history

                    # convert datetimes to ISO strings
                    def serialize_messages(items):
                        out = []
                        for m in items:
                            try:
                                mm = dict(m)
                            except Exception:
                                mm = m
                            ca = mm.get("created_at")
                            if isinstance(ca, datetime.datetime):
                                mm["created_at"] = ca.isoformat()
                            out.append(mm)
                        return out

                    messages_payload = serialize_messages(raw_messages)

                    ws_service.manager.send_personal_sync(
                        user_id,
                        {
                            "type": "history_update",
                            "chat_id": chat.id,
                            "messages": messages_payload,
                        },
                    )

                    # if recipient is viewing this chat, also push the updated history to them
                    if recipient_viewing:
                        ws_service.manager.send_personal_sync(
                            to_id,
                            {
                                "type": "history_update",
                                "chat_id": chat.id,
                                "messages": messages_payload,
                            },
                        )

                except Exception as e:
                    # log the exception or handle it as needed
                    print(f"Error updating chat history: {e}")

    except WebSocketDisconnect:
        ws_service.manager.disconnect(websocket, user_id)
    except Exception as e:
        ws_service.manager.disconnect(websocket, user_id)
        print(f"Unexpected error: {e}")
        raise
