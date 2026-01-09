from sqlalchemy import Column, Integer, String
from app.database import Base

class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    psid = Column(String, unique=True, nullable=False)
    rank = Column(String, nullable=False)
    department = Column(String, nullable=False)
    photo = Column(String, nullable=False)
    qr_hash = Column(String, unique=True, nullable=False)
    status = Column(String, default="ACTIVE")
