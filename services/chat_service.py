# chat service
import contextlib
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # add

from database import SessionLocal
from entities.chat import Chat
from services import ws_service


def create_chat(user_to_id: int, user_from_id: int, text: str, image_url: str = None):
    """Create a new chat message."""
    db = SessionLocal()
    try:
        chat = Chat(
            user_to_id=user_to_id,
            user_from_id=user_from_id,
            text=text,
            image_url=image_url,
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        # notify recipient in real-time (non-blocking)
        with contextlib.suppress(Exception):
            ws_service.manager.send_personal_sync(
                user_to_id,
                {
                    "type": "new_message",
                    "chat_id": chat.id,
                    "from": user_from_id,
                    "text": chat.text,
                },
            )
            # update unread count for recipient
            unread = count_unread_chats_for_user(user_to_id)
            ws_service.manager.send_personal_sync(
                user_to_id, {"type": "unread_count", "count": unread}
            )
        return chat
    finally:
        db.close()


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
            try:
                ws_service.manager.send_personal_sync(
                    chat.user_from_id,
                    {
                        "type": "message_seen",
                        "chat_id": chat.id,
                        "by": chat.user_to_id,
                    },
                )
                # update unread count for sender
                unread = count_unread_chats_for_user(chat.user_from_id)
                ws_service.manager.send_personal_sync(
                    chat.user_from_id, {"type": "unread_count", "count": unread}
                )
            except Exception:
                pass
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
            try:
                ws_service.manager.send_personal_sync(
                    chat.user_from_id,
                    {"type": "message_sent", "chat_id": chat.id},
                )
            except Exception:
                pass
            return chat
        return None
    finally:
        db.close()


def count_unread_chats_for_user(user_id: int):
    """Count the number of unread chat messages for a given user."""
    db = SessionLocal()
    try:
        return (
            db.query(Chat)
            .filter(Chat.user_to_id == user_id, Chat.is_seen == False)
            .count()
        )
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


def get_conversation_between_users(user1_id: int, user2_id: int):
    """Get the conversation (chat messages) between two users."""
    db = SessionLocal()
    try:
        return (
            db.query(Chat)
            .filter(
                ((Chat.user_to_id == user1_id) & (Chat.user_from_id == user2_id))
                | ((Chat.user_to_id == user2_id) & (Chat.user_from_id == user1_id))
            )
            .order_by(Chat.created_at.asc())
            .all()
        )
    finally:
        db.close()


def get_recent_chats_for_user(user_id: int, limit: int = 20):
    """Get the most recent chat messages for a given user."""
    db = SessionLocal()
    try:
        return (
            db.query(Chat)
            .filter((Chat.user_to_id == user_id) | (Chat.user_from_id == user_id))
            .order_by(Chat.created_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


def get_unread_chats_for_user(user_id: int):
    """Get all unread chat messages for a given user."""
    db = SessionLocal()
    try:
        return (
            db.query(Chat)
            .filter(Chat.user_to_id == user_id, Chat.is_seen == False)
            .order_by(Chat.created_at.desc())
            .all()
        )
    finally:
        db.close()


def get_sent_chats_for_user(user_id: int):
    """Get all chat messages sent by a given user."""
    db = SessionLocal()
    try:
        return (
            db.query(Chat)
            .filter(Chat.user_from_id == user_id)
            .order_by(Chat.created_at.desc())
            .all()
        )
    finally:
        db.close()


def get_received_chats_for_user(user_id: int):
    """Get all chat messages received by a given user."""
    db = SessionLocal()
    try:
        return (
            db.query(Chat)
            .filter(Chat.user_to_id == user_id)
            .order_by(Chat.created_at.desc())
            .all()
        )
    finally:
        db.close()


def get_chats_for_user_paginated(user_id: int, page: int = 1, per_page: int = 20):
    """Get paginated chat messages for a given user."""
    db = SessionLocal()
    try:
        total = (
            db.query(Chat)
            .filter((Chat.user_to_id == user_id) | (Chat.user_from_id == user_id))
            .count()
        )
        chats = (
            db.query(Chat)
            .filter((Chat.user_to_id == user_id) | (Chat.user_from_id == user_id))
            .order_by(Chat.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {
            "items": chats,
            "total": total,
            "page": page,
            "per_page": per_page,
        }
    finally:
        db.close()

def get_conversations_for_user(user_id: int):
    """Get a list of conversations for a given user, where each conversation is represented by the most recent chat message between the user and another user."""
    db = SessionLocal()
    try:
        # Get the most recent chat message for each conversation (grouped by the other user)
        conversations = (
            db.query(Chat)
            .filter((Chat.user_to_id == user_id) | (Chat.user_from_id == user_id))
            .order_by(Chat.created_at.desc())
            .all()
        )
        # Group chats by the other user
        conversation_dict = {}
        for chat in conversations:
            other_user_id = chat.user_from_id if chat.user_to_id == user_id else chat.user_to_id
            if other_user_id not in conversation_dict:
                conversation_dict[other_user_id] = chat  # store the most recent chat for this conversation
        return list(conversation_dict.values())
    finally:
        db.close()
        
def get_conversation_partners_for_user(user_id: int):
    """Get a list of unique conversation partners (other user IDs) for a given user."""
    db = SessionLocal()
    try:
        sent_partners = (
            db.query(Chat.user_to_id)
            .filter(Chat.user_from_id == user_id)
            .distinct()
            .all()
        )
        received_partners = (
            db.query(Chat.user_from_id)
            .filter(Chat.user_to_id == user_id)
            .distinct()
            .all()
        )
        # Combine and deduplicate partner IDs
        partner_ids = {partner[0] for partner in sent_partners + received_partners}
        return list(partner_ids)
    finally:
        db.close()