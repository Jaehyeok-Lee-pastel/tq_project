from pydantic import BaseModel


class Message(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str
