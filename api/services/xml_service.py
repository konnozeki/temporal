from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import case, not_, func, delete
from fastapi import UploadFile, File
from db.models import XmlFile
from typing import Optional
import xml.etree.ElementTree as ET
import xmltodict
from .git_service import GitService
import os


class XmlService:
    def __init__(self):
        self.git = GitService(repo_path="./xml_repo", remote_url=os.getenv("GIT_REPO_URL"), token=os.getenv("GIT_ACCESS_TOKEN"))

    async def extract_system_info(self, xml_content: str):
        try:
            root = ET.fromstring(xml_content)
            return root.attrib.get("system_code"), root.attrib.get("sub_system_code"), root.attrib.get("module_code"), root.attrib.get("module")
        except:
            return None, None, None, None

    def success_response(self, message: str = None, data=None, info=None):
        response = {"status": "success", "code": 200, "data": data}
        if message:
            response["message"] = message
        if info:
            response["info"] = info
        return response

    def error_response(self, message: str, code=600):
        return {"status": "error", "code": code, "message": message}

    async def handle_uploaded_xml_files(self, files, session: AsyncSession):
        try:
            results = []
            written_files = []

            for file in files:
                content = await file.read()
                content_decoded = content.decode()
                system, sub_system, module_code, category = await self.extract_system_info(content_decoded)

                # Tạo bản ghi DB
                xml_file = XmlFile(
                    filename=file.filename,
                    system=system,
                    sub_system=sub_system,
                    content=content_decoded,
                    module=module_code,
                    category=category,
                )
                session.add(xml_file)
                await session.flush()  # để lấy xml_file.id

                # Ghi file vào Git repo
                file_name = xml_file.filename or f"xml_{xml_file.id}.xml"
                file_path = self.git.write_file(content_id=str(xml_file.id), filename=file_name, content=xml_file.content, system=xml_file.system.lower())
                written_files.append(file_path)
                results.append(file.filename)

            await session.commit()

            # Commit và push Git nếu có file
            if written_files:
                self.git.repo.index.add(written_files)
                self.git.repo.index.commit(f"Tải lên {len(written_files)} file XML: {', '.join(results)}")
                self.git.push_all()

            return self.success_response("Tải dữ liệu lên thành công", {"uploaded": results})

        except Exception as e:
            await session.rollback()
            return self.error_response("Đã xảy ra lỗi " + str(e))

    async def list_xml_files(self, session: AsyncSession):
        stmt = select(XmlFile.id, XmlFile.filename).order_by(XmlFile.created_at.desc())
        result = await session.execute(stmt)
        records = result.all()
        files = [{"id": row.id, "filename": row.filename} for row in records]
        return self.success_response(data=files)

    async def list_xml_files_by_page(self, page: int = 1, size: int = 10, idlist: str = "", session: AsyncSession = None):
        page = int(page)
        size = int(size)
        if page < 1 or size < 1:
            return self.error_response("Tham số truyền vào không hợp lệ")

        id_priority_list = []
        if idlist:
            try:
                id_priority_list = [int(i.strip()) for i in idlist.split(",") if i.strip().isdigit()]
            except ValueError:
                return self.error_response("idlist không hợp lệ")

        results = []
        if id_priority_list:
            stmt_priority = select(XmlFile).where(XmlFile.id.in_(id_priority_list)).order_by(case(*((XmlFile.id == val, i) for i, val in enumerate(id_priority_list)), else_=len(id_priority_list)))
            result_priority = await session.execute(stmt_priority)
            priority_files = result_priority.scalars().all()
            results.extend(priority_files)

        filters = []
        if id_priority_list:
            filters.append(not_(XmlFile.id.in_(id_priority_list)))

        stmt_rest = select(XmlFile).where(*filters).order_by(XmlFile.created_at.desc()).offset((page - 1)).limit(size)
        result_rest = await session.execute(stmt_rest)
        rest_files = result_rest.scalars().all()
        results.extend(rest_files)

        count_stmt = select(func.count()).select_from(XmlFile)
        total_count = (await session.execute(count_stmt)).scalar()
        total_pages = (total_count + size - 1) // size

        return self.success_response(data=results, info={"count": total_count, "current": page, "total_pages": total_pages, "size": size})

    async def delete_record(self, idlist: str = "", session: AsyncSession = None):
        if not idlist:
            return self.error_response("Danh sách ID không hợp lệ", 603)

        try:
            id_array = [int(id.strip()) for id in idlist.split(",") if id.strip().isdigit()]
            if not id_array:
                return self.error_response("Không có ID hợp lệ nào", 603)

            # Lấy các file sẽ bị xóa
            result = await session.execute(select(XmlFile).where(XmlFile.id.in_(id_array)))
            xml_files = result.scalars().all()

            deleted_files = []
            for xml_file in xml_files:
                file_name = xml_file.filename or f"xml_{xml_file.id}.xml"
                file_path = os.path.join(self.git.repo_path, file_name)

                # Xóa file vật lý nếu tồn tại
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_files.append(file_path)

            # Xóa bản ghi trong DB
            stmt = delete(XmlFile).where(XmlFile.id.in_(id_array))
            await session.execute(stmt)
            await session.commit()

            # Remove khỏi Git + commit
            if deleted_files:
                self.git.repo.index.remove(deleted_files, working_tree=True)
                self.git.repo.index.commit(f"Xóa file XML #{', '.join(map(str, id_array))}")
                self.git.push_all()

            return self.success_response("Xóa dữ liệu thành công", id_array)

        except Exception as e:
            await session.rollback()
            return self.error_response("Đã xảy ra lỗi: " + str(e))

    async def get_by_id(self, xml_file_id: int, session: AsyncSession = None):
        try:
            stmt = select(XmlFile).where(XmlFile.id == xml_file_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if not record:
                return self.error_response("Không tìm thấy bản ghi", 604)

            return self.success_response(
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
            return self.error_response("Đã xảy ra lỗi " + str(e))

    async def create_xml_file(self, request: dict = {}, session: AsyncSession = None):
        try:
            xml_file = XmlFile(**request)
            session.add(xml_file)
            await session.commit()
            await session.refresh(xml_file)

            # Ghi file XML ra Git sau khi commit DB
            file_name = xml_file.filename or f"xml_{xml_file.id}.xml"
            file_path = self.git.write_file(content_id=str(xml_file.id), filename=file_name, content=xml_file.content, system=xml_file.system.lower())
            self.git.commit_and_tag(file_path, f"Tạo file XML #{xml_file.id}", tag_name=None)
            self.git.push_all()

            return self.success_response("Tạo bản ghi thành công", request)
        except Exception as e:
            return self.error_response(f"Tạo bản ghi thất bại: {str(e)}")

    async def update_xml_file(self, id: int, request: dict = {}, session: AsyncSession = None):
        obj = await session.get(XmlFile, id)
        if not obj:
            return self.error_response("Không tìm thấy bản ghi")

        for key, value in request.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

        await session.commit()
        await session.refresh(obj)

        # Ghi file XML ra Git sau khi commit DB
        file_name = obj.filename or f"xml_{obj.id}.xml"
        file_path = self.git.write_file(content_id=str(obj.id), filename=file_name, content=obj.content, system=obj.system.lower())
        self.git.commit_and_tag(file_path, f"Cập nhật file XML #{obj.id}", tag_name=None)
        self.git.push_all()

        return self.success_response("Cập nhật dữ liệu thành công", obj)

    def extract_metadata(self, xml_dict: dict) -> dict:
        if "root" not in xml_dict:
            xml_dict = {"root": xml_dict}
        root = xml_dict["root"]
        return {"system": root.get("system_code"), "sub_system": root.get("sub_system_code"), "module": root.get("module_code"), "category": root.get("module")}

    async def import_file(self, files: list[UploadFile] = File(...), session: AsyncSession = None):
        results = []
        staged_files = []

        for file in files:
            if not file.filename.endswith(".xml"):
                results.append({"filename": file.filename, "status": "skipped", "reason": "Not an XML file"})
                continue

            try:
                content_bytes = await file.read()
                content_str = content_bytes.decode("utf-8")
                xml_dict = xmltodict.parse(content_str)
                metadata = self.extract_metadata(xml_dict)

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

                    file_path = self.git.write_file(content_id=str(existing.id), filename=file.filename, content=content_str, system=metadata.get("system").lower())
                    staged_files.append(file_path)

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

                    file_path = self.git.write_file(content_id=str(new_file.id), filename=file.filename, content=content_str, system=metadata.get("system").lower())
                    staged_files.append(file_path)

                    results.append({"filename": file.filename, "status": "imported", "id": new_file.id})

            except Exception as e:
                results.append({"filename": file.filename, "status": "error", "reason": str(e)})

        # Commit sau khi import toàn bộ
        if staged_files:
            self.git.repo.index.add(staged_files)
            self.git.repo.index.commit(f"Import XML files: {', '.join([os.path.basename(f) for f in staged_files])}")
            self.git.push_all()

        return {"results": results}

    async def sync_git_to_db(self, session: AsyncSession):
        repo_path = self.git.repo_path
        synced = []

        for fname in os.listdir(repo_path):
            if not fname.endswith(".xml"):
                continue

            file_path = os.path.join(repo_path, fname)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            stmt = select(XmlFile).where(XmlFile.filename == fname).limit(1)
            result = await session.execute(stmt)
            existing = result.scalars().first()

            if not existing:
                system, sub_system, module_code, category = await self.extract_system_info(content)
                new_file = XmlFile(
                    filename=fname,
                    content=content,
                    system=system,
                    sub_system=sub_system,
                    module=module_code,
                    category=category,
                )
                session.add(new_file)
                synced.append(f"[+] {fname} added to DB")
            elif existing.content.strip() != content.strip():
                existing.content = content
                synced.append(f"[~] {fname} updated in DB")

        await session.commit()
        return self.success_response("Đã sync Git → DB", {"synced": synced})

    async def sync_db_to_git(self, session: AsyncSession):
        result = await session.execute(select(XmlFile))
        all_files = result.scalars().all()

        written = []
        for record in all_files:
            file_path = self.git.write_file(content_id=str(record.id), filename=record.filename, content=record.content, system=record.system.lower())
            written.append(file_path)

        if written:
            self.git.repo.index.add(written)
            self.git.repo.index.commit("Đồng bộ từ DB → Git")
            self.git.push_all()

        return self.success_response("Đã sync DB → Git", {"written": [os.path.basename(p) for p in written]})
