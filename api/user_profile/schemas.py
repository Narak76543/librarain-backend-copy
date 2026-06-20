from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class UserProfileResponse(BaseModel):
    id:               UUID
    user_id:          UUID
    first_name:       Optional[str] = None
    last_name:        Optional[str] = None
    first_name_local: Optional[str] = None
    last_name_local:  Optional[str] = None
    phone:            Optional[str] = None
    telegram:         Optional[str] = None
    address:          Optional[str] = None
    avatar_url:       Optional[str] = None
    created_at:       datetime
    updated_at:       Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    first_name:       Optional[str] = None
    last_name:        Optional[str] = None
    first_name_local: Optional[str] = None
    last_name_local:  Optional[str] = None
    phone:            Optional[str] = None
    telegram:         Optional[str] = None
    address:          Optional[str] = None

class FCMTokenRequest(BaseModel):
    fcm_token: str