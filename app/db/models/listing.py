from sqlalchemy import Column, String, Integer
from app.db.base import Base

class Listing(Base):
    __tablename__ = "listings"
    id = Column(String, primary_key=True)
    title = Column(String)
    monthly_rent = Column(Integer)
