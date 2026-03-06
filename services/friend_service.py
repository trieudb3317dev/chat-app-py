import os
from typing import List, Dict, Optional
from sqlalchemy import or_

from sqlalchemy.orm import Session
from entities.friend import Friend
from entities.user import User


def add_friend(db: Session, user_id: int, friend_id: int) -> Friend:
    """Create a friend relationship (pending) between user_id and friend_id."""
    if user_id == friend_id:
        raise ValueError("Cannot add yourself as a friend")

    if existing := (
        db.query(Friend)
        .filter(
            ((Friend.user_id == user_id) & (Friend.friend_id == friend_id))
            | ((Friend.user_id == friend_id) & (Friend.friend_id == user_id))
        )
        .first()
    ):
        raise ValueError("Friendship already exists")

    # Create pending friendship (user_id -> friend_id)
    friendship = Friend(user_id=user_id, friend_id=friend_id, is_active=False)
    db.add(friendship)
    db.commit()
    db.refresh(friendship)
    return friendship


def accept_friend(db: Session, user_id: int, friend_id: int) -> Friend:
    """Accept a pending friend request where friend_id is the requester and user_id is the recipient."""
    friendship = (
        db.query(Friend)
        .filter(
            (Friend.user_id == friend_id)
            & (Friend.friend_id == user_id)
            & (Friend.is_active == False)
            & (Friend.is_accepted == False)
        )
        .first()
    )
    if not friendship:
        raise ValueError("No pending friend request found")

    friendship.is_accepted = True
    db.commit()
    db.refresh(friendship)
    return friendship


def list_friends(
    db: Session,
    user_id: int,
    page: int = 1,
    per_page: int = 20,
    q: Optional[str] = None,
) -> Dict:
    """Return paginated list of accepted friends for `user_id`.

    Supports optional search `q` which matches username, full_name or email (case-insensitive).
    Returns a dict: { items: List[User], total: int, page: int, per_page: int }
    """
    # Find accepted friendships involving the user
    friendships = (
        db.query(Friend)
        .filter(
            ((Friend.user_id == user_id) | (Friend.friend_id == user_id))
            & (Friend.is_accepted == True) & (Friend.is_active == False)
        )
        .all()
    )

    friend_ids = set()
    for f in friendships:
        if f.user_id == user_id:
            friend_ids.add(f.friend_id)
        else:
            friend_ids.add(f.user_id)

    query = db.query(User).filter(User.id.in_(friend_ids))

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                User.username.ilike(like),
                User.full_name.ilike(like),
                User.email.ilike(like),
            )
        )

    total = query.count()
    items = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # compute next/prev pages
    next_page = page + 1 if page * per_page < total else False
    prev_page = page - 1 if page > 1 else False

    return {
        "friends": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "next_page": next_page,
        "prev_page": prev_page,
    }
