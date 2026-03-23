import os
from typing import List, Dict, Optional
from sqlalchemy import or_, func

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
            (
                ((Friend.user_id == user_id) & (Friend.friend_id == friend_id))
                | ((Friend.user_id == friend_id) & (Friend.friend_id == user_id))
            )
            & (Friend.is_active == False)
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


def remove_friend(db: Session, user_id: int, friend_id: int) -> None:
    """Remove an existing friendship between user_id and friend_id."""
    friendship = (
        db.query(Friend)
        .filter(
            ((Friend.user_id == user_id) & (Friend.friend_id == friend_id))
            | ((Friend.user_id == friend_id) & (Friend.friend_id == user_id))
        )
        .first()
    )
    if not friendship:
        raise ValueError("No friendship exists to remove")

    # db.delete(friendship)
    friendship.is_active = True  # mark as inactive instead of deleting
    db.commit()


def list_unaccepted_friend_requests(
    db: Session,
    user_id: int,
    page: int = 1,
    per_page: int = 10,
    q: Optional[str] = None,
) -> Dict:
    """List pending friend requests where user_id is the recipient."""
    # basic validation / normalization for pagination inputs
    try:
        page = page
    except (TypeError, ValueError):
        page = 1
    page = max(1, page)

    try:
        per_page = per_page
    except (TypeError, ValueError):
        per_page = 10
    # cap to avoid heavy queries
    per_page = max(1, min(per_page, 100))

    # Always join User (requester) so we can return requester fields expected by response model
    base_q = (
        db.query(Friend, User)
        .join(User, User.id == Friend.user_id)
        .filter(
            (Friend.friend_id == user_id)
            & (Friend.is_active == False)
            & (Friend.is_accepted == False)
        )
    )

    if q:
        like = f"%{q}%"
        base_q = base_q.filter(
            or_(
                User.username.ilike(like),
                User.full_name.ilike(like),
                User.email.ilike(like),
            )
        )

    total = base_q.count()
    rows = (
        base_q.order_by(Friend.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    print(
        f"list_unaccepted_friend_requests: total={total}, page={page}, per_page={per_page}, returned={len(rows)}, rows: {rows}"
    )  # debug log

    # Build serialized items that include requester fields (username etc.) so FastAPI
    # response model validation succeeds (it expects a 'username' field).
    items = []
    items.extend(
        {
            "request_id": friend.id,
            "requested_at": getattr(friend, "created_at", None),
            "user_id": user.id,
            "username": user.username,
            "full_name": getattr(user, "full_name", None),
            # "phone_number": getattr(user, "phone_number", None),
            # "day_of_birth": getattr(user, "day_of_birth", None),
            "avatar_url": getattr(user, "avatar_url", None),
            # "gender": getattr(user, "gender", None)
        }
        for friend, user in rows
    )
    next_page = page + 1 if page * per_page < total else None
    prev_page = page - 1 if page > 1 else None

    return {
        "friends": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "next_page": next_page,
        "prev_page": prev_page,
    }


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
            & (Friend.is_accepted == True)
            & (Friend.is_active == False)
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
        "friends": [{
            "id": user.id,
            "username": user.username,
            "full_name": getattr(user, "full_name", None),
            "avatar": getattr(user, "avatar_url", None),
            "email": getattr(user, "email", None),
            "phone_number": getattr(user, "phone_number", None),
            "date_of_birth": getattr(user, "date_of_birth", None),
            "gender": getattr(user, "gender", None),
            "created_at": getattr(user, "created_at", None),
        } for user in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "next_page": next_page,
        "prev_page": prev_page,
    }


def list_friend_suggestions(
    db: Session, user_id: int, page: int = 1, per_page: int = 10
) -> Dict:
    """Return a paginated list of friend suggestions for the user based on mutual friends.

    Returns dict: { items: List[User], total: int, page: int, per_page: int, next_page, prev_page }
    """
    # Get current friends
    friendships = (
        db.query(Friend)
        .filter(
            ((Friend.user_id == user_id) | (Friend.friend_id == user_id))
            & (Friend.is_accepted == True)
            & (Friend.is_active == False)
        )
        .all()
    )
    print(f"User {user_id} friendships:", friendships)  # debug log

    friend_ids = set()
    for f in friendships:
        if f.user_id == user_id:
            friend_ids.add(f.friend_id)
        else:
            friend_ids.add(f.user_id)

    print(f"User {user_id} friend IDs:", friend_ids)  # debug log
    if not friend_ids:
        return {
            "friends": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "next_page": False,
            "prev_page": False,
        }

    # Base query: users who are friends-of-friends but not already friends and not the user
    base_q = (
        db.query(User)
        .join(Friend, or_(Friend.user_id == User.id, Friend.friend_id == User.id))
        .filter(
            (Friend.is_accepted == True)
            & (Friend.is_active == False)
            & ((Friend.user_id.in_(friend_ids)) | (Friend.friend_id.in_(friend_ids)))
            & (User.id != user_id)
            & (~User.id.in_(friend_ids))
        )
        .group_by(User.id)
    )

    # total distinct users matching
    total = (
        db.query(func.count(func.distinct(User.id)))
        .select_from(User)
        .join(Friend, or_(Friend.user_id == User.id, Friend.friend_id == User.id))
        .filter(
            (Friend.is_accepted == True)
            & (Friend.is_active == False)
            & ((Friend.user_id.in_(friend_ids)) | (Friend.friend_id.in_(friend_ids)))
            & (User.id != user_id)
            & (~User.id.in_(friend_ids))
        )
        .scalar()
    )

    # order by number of mutual friends (descending)
    items = (
        base_q.order_by(func.count(Friend.id).desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    next_page = page + 1 if page * per_page < (total or 0) else False
    prev_page = page - 1 if page > 1 else False

    return {
        "friends": items,
        "total": total or 0,
        "page": page,
        "per_page": per_page,
        "next_page": next_page,
        "prev_page": prev_page,
    }


def list_unfriended_users(
    db: Session, user_id: int, page: int = 1, per_page: int = 10
) -> Dict:
    """Return a paginated list of users who are not friends with the given user.

    Returns dict: { items: List[User], total: int, page: int, per_page: int, next_page, prev_page }
    """
    # Get current friends
    friendships = (
        db.query(Friend)
        .filter(
            ((Friend.user_id == user_id) | (Friend.friend_id == user_id))
            & (Friend.is_accepted == True)
            & (Friend.is_active == False)
        )
        .all()
    )

    friend_ids = set()
    for f in friendships:
        if f.user_id == user_id:
            friend_ids.add(f.friend_id)
        else:
            friend_ids.add(f.user_id)

    # base query for users who are not friends and not the user
    base_q = db.query(User).filter((User.id != user_id) & (~User.id.in_(friend_ids)))

    total = base_q.count()
    items = (
        base_q.order_by(User.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

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
