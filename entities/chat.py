from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import relationship
from database import Base


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    user_to_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    # The `user_from_id` column in the `Chat` class is defining a foreign key relationship to the `id`
    # column in the `users` table. This column represents the user who sent the chat message. By
    # specifying `ForeignKey("users.id")`, it indicates that the `user_from_id` column in the `chats`
    # table references the `id` column in the `users` table, establishing a relationship between the
    # two tables.
    # The `user_from_id` column in the `Chat` class is defining a foreign key relationship to the `id`
    # column in the `users` table. This column represents the user who sent the chat message. By
    # specifying `ForeignKey("users.id")`, it indicates that the `user_from_id` column in the `chats`
    # table references the `id` column in the `users` table, establishing a relationship between the
    # two tables.
    user_from_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    text = Column(String, index=True, nullable=False)
    image_url = Column(String, index=True, nullable=True)

    # timestamps: set created_at and keep updated_at in sync using onupdate
    created_at = Column(DateTime(timezone=True), index=True, default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), index=True, default=func.now(), onupdate=func.now(), nullable=True)

    # delivery/read status flags
    is_seen = Column(Boolean, index=True, default=False, nullable=False)
    is_sent = Column(Boolean, index=True, default=False, nullable=False)

    # relationship to User (explicit foreign keys to avoid ambiguity)
    user_to = relationship("User", foreign_keys=[user_to_id])
    user_from = relationship("User", foreign_keys=[user_from_id])

    # def __repr__(self):
    #     return f"<Chat id={self.id} from={self.user_from_id} to={self.user_to_id} created_at={self.created_at}>"