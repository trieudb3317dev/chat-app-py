from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from . import __init__  # keep package import
from database import Base
from sqlalchemy import DateTime, Boolean
from sqlalchemy import func


class Friend(Base):
    __tablename__ = "friends"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), index=True, default=func.now())
    is_active = Column(Boolean, index=True, default=False)
    is_accepted = Column(Boolean, index=True, default=False)

    # Relationships to User model (optional, for easier access to user details)
    user = relationship("User", foreign_keys=[user_id], backref="friendships")
    friend = relationship("User", foreign_keys=[friend_id])
