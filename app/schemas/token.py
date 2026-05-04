from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class TokenPayload(BaseModel):
    sub: Optional[UUID] = None # sub biasanya diisi user_id