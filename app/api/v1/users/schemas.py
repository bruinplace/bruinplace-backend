from datetime import datetime

from pydantic import BaseModel


class MeOut(BaseModel):
    id: str
    email: str
    name: str | None = None
    profile_picture: str | None = None
    created_at: datetime
    last_login: datetime
