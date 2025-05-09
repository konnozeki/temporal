# services/xml_manager.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from db.models import XmlFile, XmlFileVersion, WorkflowRecord
from typing import Optional, List
from datetime import datetime
from uuid import uuid4
import xml.etree.ElementTree as ET


async def extract_system_info(xml_content: str):
    try:
        root = ET.fromstring(xml_content)
        system = root.attrib.get("system")
        sub_system = root.attrib.get("sub_system")
        return system, sub_system
    except ET.ParseError:
        return None, None


async def create_xml_file(session: AsyncSession, filename: str, content: str, module: Optional[str] = None, category: Optional[str] = None, workflow_id: Optional[str] = None):
    system, sub_system = await extract_system_info(content)

    xml_file = XmlFile(
        filename=filename,
        module=module,
        category=category,
        system=system,
        sub_system=sub_system,
        status="processing",
        workflow_id=workflow_id,
        version="v1",
    )
    session.add(xml_file)
    await session.flush()  # Để có xml_file.id

    version = XmlFileVersion(xml_file_id=xml_file.id, version="v1", content=content, approved=False)
    session.add(version)
    await session.commit()
    return xml_file


async def approve_xml_version(session: AsyncSession, version_id: int):
    stmt = select(XmlFileVersion).where(XmlFileVersion.id == version_id).options(selectinload(XmlFileVersion.xml_file))
    result = await session.execute(stmt)
    version = result.scalar_one_or_none()
    if not version:
        return None

    # Đánh dấu là approved
    version.approved = True
    version.xml_file.status = "approved"
    await session.commit()
    return version


async def reject_xml_file(session: AsyncSession, xml_file_id: int):
    stmt = select(XmlFile).where(XmlFile.id == xml_file_id)
    result = await session.execute(stmt)
    xml_file = result.scalar_one_or_none()
    if not xml_file:
        return None

    xml_file.status = "rejected"
    await session.commit()
    return xml_file


async def list_xml_files(session: AsyncSession, module: Optional[str] = None, category: Optional[str] = None):
    stmt = select(XmlFile).order_by(XmlFile.created_at.desc())
    if module:
        stmt = stmt.where(XmlFile.module == module)
    if category:
        stmt = stmt.where(XmlFile.category == category)

    result = await session.execute(stmt)
    return result.scalars().all()


async def get_xml_file_detail(session: AsyncSession, file_id: int):
    stmt = select(XmlFile).where(XmlFile.id == file_id).options(selectinload(XmlFile.versions))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
