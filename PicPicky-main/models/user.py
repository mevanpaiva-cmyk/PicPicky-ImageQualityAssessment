from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserModel(BaseModel):
    name: str
    email: EmailStr
    password: str
    created_at: Optional[datetime] = None