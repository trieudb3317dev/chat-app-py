from typing import List, Optional
import datetime
from pydantic import BaseModel, Field


class PostCreate(BaseModel):
    title: str
    content: Optional[str] = ""


class ItemCreate(BaseModel):
    name: str


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[str] = None  # default role is "None" or can be set to "admin", "super_admin", "editor", etc.
    
    class Config:
        orm_mode = True
        from_attributes = True  # allow population from ORM objects
    
class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    role: Optional[str] = None  # allow updating role as well, if needed
    
    class Config:
        orm_mode = True
        from_attributes = True  # allow population from ORM objects

class UserLogin(BaseModel):
    username: str
    password: str


class PostOut(BaseModel):
    id: int
    title: str

    class Config:
        orm_mode = True
        from_attributes = True  # allow population from ORM objects


class ItemOut(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True
        from_attributes = True  # allow population from ORM objects


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    role: Optional[str] = None
    avatar: Optional[str] = None
    # posts: List[PostOut] = []
    # items: List[ItemOut] = []

    class Config:
        orm_mode = True
        from_attributes = True  # allow population from ORM objects


class MessageOut(BaseModel):
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes = True  # allow population from ORM objects

class PasswordStr(BaseModel):
    """Custom type for password fields to allow for future validation or hashing logic."""
    
    # pass
    new_password: Optional[str] = None
    

# Chat schemas can be added here as needed, e.g. for messages, conversations, etc.
class ChatCreate(BaseModel):
    text: str
    user_to_id: int
    user_from_id: int
    image_url: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes = True  # allow population from ORM objects

class ChatOut(BaseModel):
    id: int
    text: str
    user_to_id: int
    user_from_id: int
    image_url: Optional[str] = None
    created_at: datetime.datetime
    is_seen: bool
    is_sent: bool
    unread: int = 0

    class Config:
        orm_mode = True
        from_attributes = True  # allow population from ORM objects


class ChatListOut(BaseModel):
    items: List[ChatOut] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 20
    next_page: Optional[int] = None
    prev_page: Optional[int] = None

    class Config:
        orm_mode = True
        from_attributes = True  # allow population from ORM objects
class FriendRequest(BaseModel):
    friend_id: int

    class Config:
        orm_mode = True
        from_attributes = True  # allow population from ORM objects

class FriendOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes = True  # allow population from ORM objects

class FriendListOut(BaseModel):
    friends: List[FriendOut] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 20
    next_page: Optional[int] = None
    prev_page: Optional[int] = None

    class Config:
        orm_mode = True
        from_attributes = True  # allow population from ORM objects