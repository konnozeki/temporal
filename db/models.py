# models.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class XmlFile(Base):
    __tablename__ = "xml_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    system = Column(String, nullable=True)
    sub_system = Column(String, nullable=True)
    module = Column(String, nullable=True)
    category = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    content = Column(Text)
