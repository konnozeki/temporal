from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from db.models import XmlFile
from sqlalchemy import func, delete
from typing import Optional
import xml.etree.ElementTree as ET


async def extract_system_info(xml_content: str):
    try:
        root = ET.fromstring(xml_content)
        return root.attrib.get("system_code"), root.attrib.get("sub_system_code"), root.attrib.get("module_code"), root.attrib.get("module")
    except:
        return None, None, None, None


def success_response(message: str = None, data=None, info=None):
    response = {
        "status": "success",
        "code": 200,
        "data": data,
    }
    if message:
        response["message"] = message
    if info:
        response["info"] = info
    return response


def error_response(message: str, code=600):
    return {
        "status": "error",
        "code": code,
        "message": message,
    }


async def handle_uploaded_xml_files(files, session: AsyncSession):
    try:
        results = []
        for file in files:
            content = await file.read()
            content_decoded = content.decode()
            system, sub_system, module_code, category = await extract_system_info(content_decoded)

            xml_file = XmlFile(filename=file.filename, system=system, sub_system=sub_system, content=content_decoded, module=module_code, category=category)
            session.add(xml_file)
            await session.flush()

            results.append(file.filename)

        await session.commit()
        return success_response("Tải dữ liệu lên thành công", {"uploaded": results})
    except Exception as e:
        await session.rollback()
        return error_response("Đã xảy ra lỗi " + str(e))


async def list_xml_files(session: AsyncSession):
    # Chỉ select các cột cần
    stmt = select(XmlFile.id, XmlFile.filename).order_by(XmlFile.created_at.desc())

    result = await session.execute(stmt)
    records = result.all()

    # Chuyển thành list[dict] nếu muốn trả JSON
    files = [{"id": row.id, "filename": row.filename} for row in records]

    return success_response(data=files)


async def list_xml_files_by_page(session: AsyncSession, page: int = 1, size: int = 10):
    page = int(page)
    size = int(size)
    if page < 1 or size < 1:
        return error_response("Tham số truyền vào không hợp lệ")

    # Chuẩn bị điều kiện lọc
    filters = []

    # Đếm tổng số bản ghi với điều kiện
    count_stmt = select(func.count()).select_from(XmlFile).where(*filters)
    total_count = (await session.execute(count_stmt)).scalar()

    # Tính toán phân trang
    total_pages = (total_count + size - 1) // size
    offset = (page - 1) * size

    # Truy vấn bản ghi theo trang và điều kiện
    stmt = select(XmlFile).where(*filters).order_by(XmlFile.created_at.desc()).offset(offset).limit(size)
    result = await session.execute(stmt)
    files = result.scalars().all()

    return success_response(
        data=files,
        info={
            "count": total_count,
            "current": page,
            "total_pages": total_pages,
            "size": size,
        },
    )


async def delete_record(idlist: str = "", session: AsyncSession = None):
    if not idlist:
        raise error_response("Danh sách ID không hợp lệ", 603)

    try:
        # Chuyển chuỗi id thành list
        id_array = [int(id.strip()) for id in idlist.split(",") if id.strip().isdigit()]
        if not id_array:
            raise error_response("Không có ID hợp lệ nào", 603)

        # Xoá các bản ghi có ID nằm trong danh sách
        stmt = delete(XmlFile).where(XmlFile.id.in_(id_array))
        await session.execute(stmt)
        await session.commit()

        return {"message": "Xóa dữ liệu thành công", "status": "success", "code": 200, "data": id_array}

    except Exception as e:
        await session.rollback()
        return error_response("Đã xảy ra lỗi " + str(e))


async def get_by_id(xml_file_id: int, session: AsyncSession = None):
    try:
        stmt = select(XmlFile).where(XmlFile.id == xml_file_id)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            raise error_response("Không tìm thấy bản ghi", 604)

        return success_response(
            data={
                "id": record.id,
                "filename": record.filename,
                "module": record.module,
                "category": record.category,
                "system": record.system,
                "sub_system": record.sub_system,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "content": record.content,
            }
        )
    except Exception as e:
        return error_response("Đã xảy ra lỗi " + str(e))


async def update_xml_file(id: int, request: dict = {}, session: AsyncSession = None):
    obj = await session.get(XmlFile, id)
    if not obj:
        return error_response("Không tìm thấy bản ghi")

    for key, value in request.items():
        if hasattr(obj, key):
            setattr(obj, key, value)

    await session.commit()
    await session.refresh(obj)
    return success_response("Cập nhật dữ liệu thành công", obj)


async def create_xml_file(request: dict = {}, session: AsyncSession = None):
    try:
        xml_file = XmlFile(**request)
        session.add(xml_file)
        await session.commit()
        await session.refresh(xml_file)
        return success_response("Tạo mới thành công", request)
    except Exception as e:
        return error_response(f"Tạo mới thất bại: {str(e)}")
