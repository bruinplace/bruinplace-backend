from sqlalchemy import Column, Integer, String
from app.db.base import BaseModel


class TestTable(BaseModel):
    __tablename__ = "test_table"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
