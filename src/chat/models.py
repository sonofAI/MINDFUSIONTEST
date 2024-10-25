from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from src.database import Base

from src.auth.models import User


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    message = Column(String)

    sender_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])