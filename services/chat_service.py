# chat service
import contextlib
import os, sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # add

from database import SessionLocal
from entities.chat import Chat
from services import ws_service
from sqlalchemy import func


def create_chat(
    user_to_id: int,
    user_from_id: int,
    text: str,
    image_url: str = None,
    *,
    notify: bool = True,
    mark_seen: bool = False,
):
    """Create a new chat message.

    Parameters:
    - notify: if True, send websocket notifications to recipient/sender.
    - mark_seen: if True, mark the message as seen immediately (used when recipient
      is currently viewing the chat) so unread count does not increase.
    """
    db = SessionLocal()
    try:
        chat = Chat(
            user_to_id=user_to_id,
            user_from_id=user_from_id,
            text=text,
            image_url=image_url,
        )
        if mark_seen:
            # set seen before committing so DB reflects the seen status
            chat.is_seen = True

        db.add(chat)
        db.commit()
        db.refresh(chat)

        if notify:
            # notify recipient in real-time (non-blocking)
            with contextlib.suppress(Exception):
                _extracted_from_create_chat_36(
                    user_to_id, chat, user_from_id, mark_seen
                )
        return chat
    finally:
        db.close()


# TODO Rename this here and in `create_chat`
def _extracted_from_create_chat_36(user_to_id, chat, user_from_id, mark_seen):
    ws_service.manager.send_personal_sync(
        user_to_id,
        {
            "type": "new_message",
            "chat_id": chat.id,
            "from": user_from_id,
            "text": chat.text,
        },
    )

    # If recipient immediately saw the message, notify sender with message_seen
    if mark_seen:
        ws_service.manager.send_personal_sync(
            user_from_id,
            {
                "type": "message_seen",
                "chat_id": chat.id,
                "by": user_to_id,
            },
        )

    # update unread counts for both parties (client can decide what to do)
    unread_recipient = count_unread_chats_for_user(user_to_id)
    ws_service.manager.send_personal_sync(
        user_to_id, {"type": "unread_count", "count": unread_recipient}
    )

    unread_sender = count_unread_chats_for_user(user_from_id)
    ws_service.manager.send_personal_sync(
        user_from_id, {"type": "unread_count", "count": unread_sender}
    )


def get_chats_for_user(user_id: int):
    """Get all chat messages for a given user (both sent and received)."""
    db = SessionLocal()
    try:
        return (
            db.query(Chat)
            .filter((Chat.user_to_id == user_id) | (Chat.user_from_id == user_id))
            .order_by(Chat.created_at.desc())
            .all()
        )
    finally:
        db.close()


def mark_chat_as_seen(chat_id: int):
    """Mark a chat message as seen."""
    db = SessionLocal()
    try:
        if chat := db.query(Chat).filter(Chat.id == chat_id).first():
            chat.is_seen = True
            db.commit()
            db.refresh(chat)
            # notify sender that recipient has seen the message
            with contextlib.suppress(Exception):
                ws_service.manager.send_personal_sync(
                    chat.user_from_id,
                    {
                        "type": "message_seen",
                        "chat_id": chat.id,
                        "by": chat.user_to_id,
                    },
                )
                # update unread count for sender
                unread = count_unread_chats_for_user_and_group_by_sender(chat.user_from_id)
                ws_service.manager.send_personal_sync(
                    chat.user_from_id, {"type": "unread_count", "count": unread}
                )
            return chat
        return None
    finally:
        db.close()


def mark_chat_as_sent(chat_id: int):
    """Mark a chat message as sent (for delivery status)."""
    db = SessionLocal()
    try:
        if chat := db.query(Chat).filter(Chat.id == chat_id).first():
            chat.is_sent = True
            db.commit()
            db.refresh(chat)
            # notify sender or recipient about sent status
            with contextlib.suppress(Exception):
                ws_service.manager.send_personal_sync(
                    chat.user_from_id,
                    {"type": "message_sent", "chat_id": chat.id},
                )
            return chat
        return None
    finally:
        db.close()

def count_unread_chats_for_user_and_group_by_sender(user_id: int) -> dict:
    """Count the number of unread chat messages for a given user."""
    db = SessionLocal()
    try:
        count = (
            db.query(Chat)
            .filter(Chat.user_to_id == user_id, Chat.is_seen == False)
            .count()
        )
        # TODO: for a more advanced version, we could group by user_from_id to get counts per sender
        sender_counts = (
            db.query(Chat.user_from_id, func.count(Chat.id))
            .filter(Chat.user_to_id == user_id, Chat.is_seen == False)
            .group_by(Chat.user_from_id)
            .all()
        )
        return {
            "unread_count": count,
            "user_id": user_id,
            "sender_counts": dict(sender_counts),
        }
    finally:
        db.close()


def delete_chat(chat_id: int):
    """Delete a chat message by ID."""
    db = SessionLocal()
    try:
        if chat := db.query(Chat).filter(Chat.id == chat_id).first():
            db.delete(chat)
            db.commit()
            return True
        return False
    finally:
        db.close()


def update_chat_text(chat_id: int, new_text: str):
    """Update the text of a chat message."""
    db = SessionLocal()
    try:
        if chat := db.query(Chat).filter(Chat.id == chat_id).first():
            chat.text = new_text
            db.commit()
            db.refresh(chat)
            return chat
        return None
    finally:
        db.close()


def update_chat_image(chat_id: int, new_image_url: str):
    """Update the image URL of a chat message."""
    db = SessionLocal()
    try:
        if chat := db.query(Chat).filter(Chat.id == chat_id).first():
            chat.image_url = new_image_url
            db.commit()
            db.refresh(chat)
            return chat
        return None
    finally:
        db.close()


def get_chat_by_id(chat_id: int):
    """Get a chat message by ID."""
    db = SessionLocal()
    try:
        return db.query(Chat).filter(Chat.id == chat_id).first()
    finally:
        db.close()


def get_conversation_between_users(
    user1_id: int,
    user2_id: int,
    page: int = 1,
    per_page: int = 20,
    q: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "asc",
):
    """Get the conversation (chat messages) between two users."""
    db = SessionLocal()
    try:
        # build base query for messages between the two users
        base_query = db.query(Chat).filter(
            ((Chat.user_to_id == user1_id) & (Chat.user_from_id == user2_id))
            | ((Chat.user_to_id == user2_id) & (Chat.user_from_id == user1_id))
        )

        # optional search on text
        if q:
            like = f"%{q}%"
            base_query = base_query.filter(Chat.text.ilike(like))

        # determine ordering safely (allow only certain fields)
        allowed_sort_fields = {"created_at": Chat.created_at, "id": Chat.id}
        sort_col = allowed_sort_fields.get(sort_by, Chat.created_at)
        if sort_order.lower() == "desc":
            order_clause = sort_col.desc()
        else:
            order_clause = sort_col.asc()

        total = base_query.count()

        # pagination
        page = max(page, 1)
        if per_page < 1:
            per_page = 20
        offset = (page - 1) * per_page

        messages = (
            base_query.order_by(order_clause).offset(offset).limit(per_page).all()
        )

        # build serialized list matching ChatOut schema
        items = []
        items.extend(
            {
                "id": message.id,
                "text": message.text,
                "user_to_id": message.user_to_id,
                "user_from_id": message.user_from_id,
                "image_url": message.image_url,
                "created_at": message.created_at,
                "is_seen": message.is_seen,
                # unread — for the requesting user (user1_id) indicate unread status
                "unread": (
                    1 if (message.user_to_id == user1_id and not message.is_seen) else 0
                ),
                # is_sent: True when message was sent by the requester
                "is_sent": (
                    True if (message.user_from_id == user1_id) else message.is_sent
                ),
            }
            for message in messages
        )
        # next/prev page calculation
        next_page = page + 1 if offset + len(items) < total else None
        prev_page = page - 1 if page > 1 else None

        if not items:
            # ensure we always return the expected structure even if no messages
            items = []

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "next_page": next_page,
            "prev_page": prev_page,
        }
    finally:
        db.close()
