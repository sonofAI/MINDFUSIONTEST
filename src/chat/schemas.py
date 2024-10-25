from pydantic import BaseModel


class MessagesModel(BaseModel):
    id: int
    sender_id: int
    receiver_id: int

    class Config:
        orm_mode = True