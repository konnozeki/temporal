from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import case, not_
from sqlalchemy.orm import selectinload
from db.models import XmlFile
from sqlalchemy import func, delete
from typing import Optional
import xml.etree.ElementTree as ET
import xmltodict
from fastapi import UploadFile, File


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


async def list_xml_files_by_page(session: AsyncSession, page: int = 1, size: int = 10, idlist: str = ""):
    page = int(page)
    size = int(size)
    if page < 1 or size < 1:
        return error_response("Tham số truyền vào không hợp lệ")

    # Parse idlist
    id_priority_list = []
    if idlist:
        try:
            id_priority_list = [int(i.strip()) for i in idlist.split(",") if i.strip().isdigit()]
        except ValueError:
            return error_response("idlist không hợp lệ")

    results = []

    # 1. Lấy các bản ghi trong id_priority_list
    if id_priority_list:
        stmt_priority = select(XmlFile).where(XmlFile.id.in_(id_priority_list)).order_by(case(*((XmlFile.id == val, i) for i, val in enumerate(id_priority_list)), else_=len(id_priority_list)))
        result_priority = await session.execute(stmt_priority)
        priority_files = result_priority.scalars().all()
        results.extend(priority_files)

    filters = []
    if id_priority_list:
        filters.append(not_(XmlFile.id.in_(id_priority_list)))

    stmt_rest = select(XmlFile).where(*filters).order_by(XmlFile.created_at.desc()).offset((page - 1)).limit(size)  # offset chỉ khi không có ưu tiên
    result_rest = await session.execute(stmt_rest)
    rest_files = result_rest.scalars().all()
    results.extend(rest_files)

    # Đếm tổng số bản ghi
    count_stmt = select(func.count()).select_from(XmlFile)
    total_count = (await session.execute(count_stmt)).scalar()
    total_pages = (total_count + size - 1) // size

    return success_response(
        data=results,
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
        print(request, "request")
        xml_file = XmlFile(**request)
        session.add(xml_file)
        await session.commit()
        await session.refresh(xml_file)
        return success_response("Tạo bản ghi thành công", request)
    except Exception as e:
        return error_response(f"Tạo bản ghi thất bại: {str(e)}")


def extract_metadata(xml_dict: dict) -> dict:
    if "root" not in xml_dict:
        xml_dict = {"root": xml_dict}
    root = xml_dict["root"]
    return {"system": root.get("system_code"), "sub_system": root.get("sub_system_code"), "module": root.get("module_code"), "category": root.get("module")}


async def import_file(files: list[UploadFile] = File(...), session: AsyncSession = None):
    results = []

    for file in files:
        if not file.filename.endswith(".xml"):
            results.append({"filename": file.filename, "status": "skipped", "reason": "Not an XML file"})
            continue

        try:
            content_bytes = await file.read()
            content_str = content_bytes.decode("utf-8")

            xml_dict = xmltodict.parse(content_str)
            metadata = extract_metadata(xml_dict)

            # Truy vấn async
            stmt = select(XmlFile).where(XmlFile.filename == file.filename).limit(1)
            result = await session.execute(stmt)
            existing = result.scalars().first()

            if existing:
                existing.content = content_str
                existing.system = metadata.get("system")
                existing.sub_system = metadata.get("sub_system")
                existing.module = metadata.get("module")
                existing.category = metadata.get("category")
                await session.commit()
                await session.refresh(existing)
                results.append({"filename": file.filename, "status": "updated", "id": existing.id})
            else:
                new_file = XmlFile(
                    filename=file.filename,
                    content=content_str,
                    system=metadata.get("system"),
                    sub_system=metadata.get("sub_system"),
                    module=metadata.get("module"),
                    category=metadata.get("category"),
                )
                session.add(new_file)
                await session.commit()
                await session.refresh(new_file)
                results.append({"filename": file.filename, "status": "imported", "id": new_file.id})

        except Exception as e:
            results.append({"filename": file.filename, "status": "error", "reason": str(e)})

    return {"results": results}
