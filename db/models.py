# models.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


# --- Enum trạng thái workflow ---
class WorkflowStatusEnum(str, enum.Enum):
    processing = "processing"
    completed = "completed"
    failed = "failed"
    rejected = "rejected"
    approved = "approved"


# --- Bảng lưu trạng thái workflow ---
class WorkflowRecord(Base):
    __tablename__ = "workflow_records"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(String, unique=True, index=True)
    module = Column(String)  # FE, BE, XML
    status = Column(Enum(WorkflowStatusEnum), default=WorkflowStatusEnum.processing)
    result_path = Column(String, nullable=True)  # Đường dẫn file zip kết quả
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# --- Cây phân loại module / category ---
class XmlCategory(Base):
    __tablename__ = "xml_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    parent_id = Column(Integer, ForeignKey("xml_categories.id"), nullable=True)

    children = relationship("XmlCategory", backref="parent", remote_side=[id])


# --- Bảng quản lý file XML ---
class XmlFile(Base):
    __tablename__ = "xml_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    module = Column(String, nullable=True)  # hrm, fin...
    category = Column(String, nullable=True)  # department, quote...
    system = Column(String, nullable=True)
    sub_system = Column(String, nullable=True)
    version = Column(String, default="v1")
    status = Column(Enum(WorkflowStatusEnum), default=WorkflowStatusEnum.processing)
    workflow_id = Column(String, ForeignKey("workflow_records.workflow_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workflow = relationship("WorkflowRecord", backref="xml_files")


# --- Bảng quản lý các phiên bản XML ---
class XmlFileVersion(Base):
    __tablename__ = "xml_file_versions"

    id = Column(Integer, primary_key=True, index=True)
    xml_file_id = Column(Integer, ForeignKey("xml_files.id"))
    version = Column(String, default="v1")
    content = Column(Text)
    approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    xml_file = relationship("XmlFile", backref="versions")
