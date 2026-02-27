from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from . import __init__  # keep package import
from database import Base
from sqlalchemy import func
from sqlalchemy import DateTime, Boolean

class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    user_to_id = Column(Integer, ForeignKey("users.id"), index=True)
    user_from_id = Column(Integer, ForeignKey("users.id"), index=True)
    text = Column(String, index=True, nullable=False)
    image_url = Column(String, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), index=True, default=func.now())
    updated_at = Column(DateTime(timezone=True), index=True, default=None)
    
    un_read = Column(Integer, index=True, default=0)  # new column to track unread messages
    is_seen = Column(Boolean, index=True, default=False)  # new column to track if message has been seen
    is_sent = Column(Boolean, index=True, default=False)  # new column to track if message has been sent (for delivery status)

    # relationship to User
    user_to = relationship("User", foreign_keys=[user_to_id])
    user_from = relationship("User", foreign_keys=[user_from_id])