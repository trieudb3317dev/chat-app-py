import uuid
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Table,
    Text,
    DateTime,
    Boolean,
)
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from . import __init__  # keep package import
from database import Base
from enum import Enum

# Association table for many-to-many between users and items
# user_items = Table(
#     "user_items",
#     Base.metadata,
#     Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
#     Column("item_id", Integer, ForeignKey("items.id"), primary_key=True),
# )


class User(Base):
    __tablename__ = "users"

    # Use native PostgreSQL UUID type. as_uuid=True maps values to python uuid.UUID objects.
    # id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    password = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String, index=True, nullable=True)
    address = Column(String, index=True, nullable=True)
    phone_number = Column(String, index=True, nullable=True)
    date_of_birth = Column(String, index=True, nullable=True)
    gender = Column(String, index=True, nullable=True)
    # store timestamp as a DateTime and default to current timestamp on the DB server
    created_at = Column(DateTime(timezone=True), index=True, default=func.now())
    # last_login = Column(String, index=True)
    is_active = Column(Boolean, index=True, default=False)

    # # one-to-many: User -> Post
    # posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")

    # # many-to-many: User <-> Item
    # items = relationship("Item", secondary=user_items, back_populates="users")


# Enum for user roles (optional, can also use a string column as above)
class UserRole(str, Enum):
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    EDITOR = "editor"


class UserAdmin(Base):
    __tablename__ = "user_admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    password = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    # Enum for user roles (optional, can also use a string column as above)
    role = Column(String, index=True, default=UserRole.ADMIN.value, nullable=False)
    full_name = Column(String, index=True, nullable=True)
    address = Column(String, index=True, nullable=True)
    phone_number = Column(String, index=True, nullable=True)
    date_of_birth = Column(String, index=True, nullable=True)
    gender = Column(String, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), index=True, default=func.now())
    is_active = Column(Boolean, index=True, default=False)


# class Post(Base):
#     __tablename__ = "posts"

#     id = Column(Integer, primary_key=True, index=True)
#     title = Column(String, index=True)
#     content = Column(Text)

#     # n-1 (many posts belong to one user)
#     user_id = Column(Integer, ForeignKey("users.id"))
#     author = relationship("User", back_populates="posts")


# class Item(Base):
#     __tablename__ = "items"

#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String, unique=True, index=True)

#     # many-to-many reverse
#     users = relationship("User", secondary=user_items, back_populates="items")
