# models.py
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

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


class GitJob(Base):
    __tablename__ = "git_jobs"

    id = Column(Integer, primary_key=True, index=True)
    direction = Column(String, nullable=False, unique=True, index=True)
    workflow_id = Column(String, nullable=False, unique=True, index=True)
    status = Column(String, nullable=False, index=True)
    last_error = Column(Text, nullable=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
