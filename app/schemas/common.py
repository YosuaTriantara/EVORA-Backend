from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic pagination wrapper untuk semua list endpoint.

    Contoh penggunaan:
        response_model=PaginatedResponse[UserReadFull]
        response_model=PaginatedResponse[EventReadFull]
    """

    total: int
    skip: int
    limit: int
    data: List[T]


class MessageResponse(BaseModel):
    """Response sederhana untuk operasi yang hanya mengembalikan pesan."""

    message: str
