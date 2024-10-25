from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import insert, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker, get_async_session
from .models import Message
from .schemas import MessagesModel

from typing import Dict, List


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_message(self, sender_id: int, receiver_id: int, message: str, websocket: WebSocket, add_to_db: bool):
        receiver_websocket = self.active_connections.get(receiver_id)
        if receiver_websocket:
            if add_to_db:
                await self.add_message_to_db(sender_id=sender_id, receiver_id=receiver_id, message=message)
            await receiver_websocket.send_text(message)
        else:
            # send notification with bot
            pass

    async def broadcast(self, sender_id: int, message: str):
        for user_id, websocket in self.active_connections.items():
            if user_id != sender_id:
                await websocket.send_text(message)


    @staticmethod
    async def add_message_to_db(sender_id: int, receiver_id: int, message: str):
        async with async_session_maker() as session:
            stmt = insert(Message).values(sender_id=sender_id, receiver_id=receiver_id, message=message)
            await session.execute(stmt)
            await session.commit()
            print(f"saved {message}, {receiver_id} -> {sender_id}")


manager = ConnectionManager()


@router.websocket("/ws/{sender_id}/{receiver_id}")
async def websocket_endpoint(websocket: WebSocket, sender_id: int, receiver_id: int):
    await manager.connect(websocket=websocket, user_id=sender_id)
    await manager.broadcast(sender_id=sender_id, message=f"User {sender_id} is online.")
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_message(sender_id=sender_id, receiver_id=receiver_id, message=data, websocket=websocket, add_to_db=True)

    except WebSocketDisconnect:
        manager.disconnect(sender_id)
        await manager.broadcast(sender_id=sender_id, message=f"User {sender_id} is offline.")
        

@router.get("/history/{sender_id}/{receiver_id}")
async def get_history(sender_id: int, receiver_id: int, session: AsyncSession = Depends(get_async_session)):
    stmt = (
        select(Message)
        .where(
            or_(
                (Message.sender_id == sender_id) & (Message.receiver_id == receiver_id),
                (Message.sender_id == receiver_id) & (Message.receiver_id == sender_id),
            )
        )
        .order_by(Message.id.asc())  # Fetch messages in chronological order
    )
    result = await session.execute(stmt)
    messages = result.scalars().all()
    return messages