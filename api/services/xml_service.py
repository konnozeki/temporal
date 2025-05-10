from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from db.models import XmlFile, XmlFileVersion
from typing import Optional
import xml.etree.ElementTree as ET


async def extract_system_info(xml_content: str):
    try:
        root = ET.fromstring(xml_content)
        return root.attrib.get("system"), root.attrib.get("sub_system")
    except ET.ParseError:
        return None, None


def success_response(message: str, data=None):
    return {
        "status": "success",
        "code": 200,
        "message": message,
        "data": data,
    }


def error_response(message: str):
    return {
        "status": "error",
        "code": 200,
        "message": message,
        "data": None,
    }


async def handle_uploaded_xml_files(files, session: AsyncSession):
    results = []
    for file in files:
        content = await file.read()
        system, sub_system = await extract_system_info(content.decode())

        xml_file = XmlFile(
            filename=file.filename,
            system=system,
            sub_system=sub_system,
            status="processing",
            version="v1",
        )
        session.add(xml_file)
        await session.flush()

        version = XmlFileVersion(xml_file_id=xml_file.id, version="v1", content=content.decode(), approved=False)
        session.add(version)
        results.append(file.filename)

    await session.commit()
    return success_response("Tải lên thành công", {"uploaded": results})


async def list_xml_files(session: AsyncSession):
    stmt = select(XmlFile).order_by(XmlFile.created_at.desc())
    result = await session.execute(stmt)
    files = result.scalars().all()
    return success_response("Danh sách file XML", files)


async def get_file_versions(xml_file_id: int, session: AsyncSession):
    stmt = select(XmlFile).where(XmlFile.id == xml_file_id).options(selectinload(XmlFile.versions))
    result = await session.execute(stmt)
    xml_file = result.scalar_one_or_none()
    if xml_file:
        return success_response(f"Các phiên bản của file ID {xml_file_id}", xml_file.versions)
    return error_response("Không tìm thấy file XML")


async def approve_xml_version(xml_file_id: int, version_id: int, session: AsyncSession):
    stmt = select(XmlFileVersion).where(XmlFileVersion.id == version_id)
    result = await session.execute(stmt)
    version = result.scalar_one_or_none()
    if version and version.xml_file_id == xml_file_id:
        version.approved = True
        stmt2 = select(XmlFile).where(XmlFile.id == xml_file_id)
        result2 = await session.execute(stmt2)
        xml_file = result2.scalar_one()
        xml_file.status = "approved"
        await session.commit()
        return success_response("Phê duyệt thành công", {"approved_version_id": version_id})
    return error_response("Không tìm thấy phiên bản")
