from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import case, not_, func, delete
from fastapi import UploadFile, File
from temporalio.client import Client
from db.models import XmlFile
import xml.etree.ElementTree as ET
import xmltodict
import os

from .git_service import get_git_service
from .git_sync_service import enqueue_git_sync

MODULE_CONFIGURATION_LIST = ["fob", "hrm", "fin", "re", "util", "mes"]


class XmlService:
    """
    Dịch vụ xử lý file XML.
    - Quản lý các thao tác với file XML như tải lên, liệt kê, xóa, cập nhật và đồng bộ với Git.
    - Tự động trích xuất thông tin hệ thống từ nội dung XML.
    - Cung cấp các phương thức để xử lý file XML và tương tác với cơ sở dữ liệu.
    - Sử dụng GitService để ghi file vào repository và quản lý các thay đổi.
    - Các phương thức:
        + `extract_system_info(xml_content)`: Trích xuất thông tin hệ thống từ nội dung XML.
        + `success_response(message, data, info)`: Tạo phản hồi thành công với dữ liệu và thông tin bổ sung.
        + `error_response(message, code)`: Tạo phản hồi lỗi với mã lỗi và thông điệp.
        + `handle_uploaded_xml_files(files, session)`: Xử lý các file XML được tải lên, lưu vào DB và ghi vào Git.
        + `list_xml_files(session)`: Liệt kê tất cả các file XML trong cơ sở dữ liệu.
        + `list_xml_files_by_page(page, size, idlist, session)`: Liệt kê các file XML theo trang với tùy chọn lọc theo ID.
        + `delete_record(idlist, session)`: Xóa các bản ghi XML theo danh sách ID.
        + `get_by_id(xml_file_id, session)`: Lấy thông tin file XML theo ID.
        + `create_xml_file(request, session)`: Tạo bản ghi XML mới từ yêu cầu.
        + `update_xml_file(id, request, session)`: Cập nhật thông tin file XML theo ID.
        + `extract_metadata(xml_dict)`: Trích xuất metadata từ dict XML.
        + `import_file(files, session)`: Nhập file XML từ danh sách file tải lên.
        + `sync_git_to_db(session)`: Đồng bộ dữ liệu từ Git repository vào cơ sở dữ liệu.
        + `sync_db_to_git(session)`: Đồng bộ dữ liệu từ cơ sở dữ liệu lên Git repository.
    - Sử dụng SQLAlchemy để tương tác với cơ sở dữ liệu.
    - Sử dụng xmltodict để chuyển đổi giữa XML và dict.
    - Sử dụng GitService để quản lý các thao tác với Git repository.
    """

    def __init__(self):
        self.git = None

    async def extract_system_info(self, xml_content: str):
        """
        Trích xuất thông tin hệ thống từ nội dung XML.
        - Trả về tuple gồm system_code, sub_system_code, module_code và module.
        - Nếu không thể phân tích cú pháp XML, trả về None cho tất cả các giá trị.
        """
        try:
            root = ET.fromstring(xml_content)
            return root.find("system_code").text, root.find("sub_system_code").text, root.find("module_code").text, root.find("module").text
        except:
            return None, None, None, None

    def success_response(self, message: str = None, data=None, info=None):
        """
        Tạo phản hồi thành công với dữ liệu và thông tin bổ sung.
        - `message`: Thông điệp thành công (tùy chọn).
        - `data`: Dữ liệu trả về (tùy chọn).
        - `info`: Thông tin bổ sung (tùy chọn).
        """
        response = {"status": "success", "code": 200, "data": data}
        if message:
            response["message"] = message
        if info:
            response["info"] = info
        return response

    def error_response(self, message: str, code=600):
        """
        Tạo phản hồi lỗi với mã lỗi và thông điệp.
        - `message`: Thông điệp lỗi.
        - `code`: Mã lỗi (mặc định là 600).
        - Trả về một dict chứa thông tin lỗi.
        """
        return {"status": "error", "code": code, "message": message}

    async def handle_uploaded_xml_files(self, files, session: AsyncSession, client: Client = None):
        """
        Xử lý các file XML được tải lên, lưu vào cơ sở dữ liệu và ghi vào Git repository.
        - Các tham số
            + `files`: Danh sách các file UploadFile được tải lên.
            + `session`: Phiên làm việc với cơ sở dữ liệu (AsyncSession).
        - Trả về phản hồi thành công với danh sách các file đã tải lên.
        - Nếu có lỗi xảy ra, trả về phản hồi lỗi với thông điệp chi tiết.
        - Tự động trích xuất thông tin hệ thống từ nội dung XML và lưu vào cơ sở dữ liệu.
        """
        try:
            results = []
            for file in files:
                content = await file.read()
                content_decoded = content.decode()
                system, sub_system, module_code, category = await self.extract_system_info(content_decoded)
                xml_file = XmlFile(filename=file.filename, system=system, sub_system=sub_system, content=content_decoded, module=module_code, category=category)
                session.add(xml_file)
                results.append(file.filename)
            await session.commit()
            workflow_id = await self._enqueue_db_to_git_sync(client)

            return self.success_response("Tải dữ liệu lên thành công", {"uploaded": results, "workflow_id": workflow_id})

        except Exception as e:
            await session.rollback()
            return self.error_response("Đã xảy ra lỗi " + str(e))

    async def list_xml_files(self, session: AsyncSession):
        """
        Trả về danh sách các file XML đã được lưu trữ trong cơ sở dữ liệu.
        - Các tham số:
            + `session`: Phiên làm việc với cơ sở dữ liệu (AsyncSession).
        - Thực hiện:
            + Truy vấn tất cả các bản ghi `XmlFile` đã lưu, sắp xếp theo thời gian tạo mới nhất.
            + Lấy `id` và `filename` của từng bản ghi để hiển thị.
        - Trả về:
            + Phản hồi thành công chứa danh sách các file có `id` và `filename`.
        """
        stmt = select(XmlFile.id, XmlFile.filename).order_by(XmlFile.created_at.desc())
        result = await session.execute(stmt)

        # delete_stmt = delete(XmlFile).where(1 == 1)
        # await session.execute(delete_stmt)
        # await session.commit()
        records = result.all()
        files = [{"id": row.id, "filename": row.filename} for row in records]
        return self.success_response(data=files)

    async def list_xml_files_by_page(self, page: int = 1, size: int = 10, idlist: str = "", session: AsyncSession = None):
        """
        Trả về danh sách các file XML theo phân trang, với khả năng ưu tiên hiển thị các file có ID chỉ định.

        - Các tham số:
            + `page` (int): Trang cần lấy, bắt đầu từ 1. Mặc định là 1.
            + `size` (int): Số lượng bản ghi mỗi trang. Mặc định là 10.
            + `idlist` (str): Chuỗi chứa các ID phân cách bởi dấu phẩy, dùng để ưu tiên hiển thị đầu tiên.
            + `session` (AsyncSession): Phiên làm việc với cơ sở dữ liệu.

        - Thực hiện:
            + Kiểm tra hợp lệ của các tham số đầu vào.
            + Nếu `idlist` được cung cấp, truy vấn các file có ID tương ứng và đưa lên đầu danh sách, theo đúng thứ tự đã truyền.
            + Truy vấn phần còn lại theo thứ tự `created_at` giảm dần, với phân trang theo `page` và `size`.
            + Tính tổng số bản ghi và số trang dựa trên `size`.

        - Trả về:
            + Phản hồi thành công chứa danh sách file XML (ưu tiên + còn lại) cùng thông tin phân trang.
            + Nếu lỗi xảy ra (ví dụ: idlist sai định dạng), trả về phản hồi lỗi với thông điệp chi tiết.
        """
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
        """
        Xóa các bản ghi XML tương ứng với danh sách ID, bao gồm cả dữ liệu trong cơ sở dữ liệu và file vật lý trong Git repository.

        - Các tham số:
            + `idlist` (str): Chuỗi chứa các ID phân cách bởi dấu phẩy (ví dụ: "1,2,3").
            + `session` (AsyncSession): Phiên làm việc với cơ sở dữ liệu.

        - Thực hiện:
            + Kiểm tra tính hợp lệ của danh sách ID đầu vào.
            + Truy vấn và lấy danh sách các bản ghi XML tương ứng.
            + Xóa các file vật lý tương ứng nếu tồn tại trong hệ thống file.
            + Xóa bản ghi trong cơ sở dữ liệu.
            + Cập nhật Git repository (xóa khỏi index, commit và push).

        - Trả về:
            + Phản hồi thành công với danh sách ID đã xóa nếu thực hiện thành công.
            + Nếu có lỗi xảy ra (ví dụ: ID không hợp lệ hoặc lỗi hệ thống), trả về phản hồi lỗi với thông điệp chi tiết.
        """
        if not idlist:
            return self.error_response("Danh sách ID không hợp lệ", 603)

        try:
            id_array = [int(id.strip()) for id in idlist.split(",") if id.strip().isdigit()]
            if not id_array:
                return self.error_response("Không có ID hợp lệ nào", 603)

            stmt = delete(XmlFile).where(XmlFile.id.in_(id_array))
            await session.execute(stmt)
            await session.commit()

            return self.success_response("Xóa dữ liệu thành công", id_array)

        except Exception as e:
            await session.rollback()
            return self.error_response(f"Đã xảy ra lỗi: {str(e)}")

    async def get_by_id(self, xml_file_id: int, session: AsyncSession = None):
        """
        Lấy thông tin chi tiết của một file XML theo ID.

        - Các tham số:
            + `xml_file_id` (int): ID của file XML cần truy vấn.
            + `session` (AsyncSession): Phiên làm việc với cơ sở dữ liệu.

        - Thực hiện:
            + Truy vấn bản ghi `XmlFile` với ID tương ứng từ cơ sở dữ liệu.
            + Nếu tìm thấy, trả về đầy đủ thông tin chi tiết bao gồm: tên file, module, category, system, sub_system, ngày tạo và nội dung XML.
            + Nếu không tìm thấy, trả về thông báo lỗi phù hợp.

        - Trả về:
            + Phản hồi thành công với dữ liệu bản ghi nếu tìm thấy.
            + Phản hồi lỗi nếu ID không tồn tại hoặc xảy ra lỗi trong quá trình truy vấn.
        """
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

    async def create_xml_file(self, request: dict = {}, session: AsyncSession = None, client: Client = None):
        """
        Tạo mới một bản ghi file XML từ dữ liệu đầu vào và ghi nội dung vào Git repository.

        - Các tham số:
            + `request` (dict): Dữ liệu đầu vào dùng để tạo bản ghi `XmlFile`, bao gồm các trường như `filename`, `content`, `system`, `sub_system`, `module`, `category`, v.v.
            + `session` (AsyncSession): Phiên làm việc với cơ sở dữ liệu.

        - Thực hiện:
            + Tạo đối tượng `XmlFile` từ dữ liệu đầu vào và lưu vào cơ sở dữ liệu.
            + Sau khi lưu thành công, ghi nội dung XML ra file vật lý và lưu vào Git repository.
            + Commit thay đổi vào Git, có thể đính kèm tag nếu cần.

        - Trả về:
            + Phản hồi thành công nếu tạo bản ghi và ghi Git thành công.
            + Trả về lỗi chi tiết nếu có lỗi xảy ra trong quá trình xử lý.
        """
        try:
            xml_file = XmlFile(**request)
            session.add(xml_file)
            await session.commit()
            workflow_id = await self._enqueue_db_to_git_sync(client)

            return self.success_response("Tạo bản ghi thành công", {**request, "workflow_id": workflow_id})
        except Exception as e:
            return self.error_response(f"Tạo bản ghi thất bại: {str(e)}")

    async def update_xml_file(self, id: int, request: dict = {}, session: AsyncSession = None, client: Client = None):
        """
        Cập nhật nội dung một bản ghi file XML và đồng bộ thay đổi với Git repository.

        - Các tham số:
            + `id` (int): ID của bản ghi `XmlFile` cần cập nhật.
            + `request` (dict): Dữ liệu cập nhật, bao gồm các trường hợp lệ như `filename`, `content`, `system`, `sub_system`, `module`, `category`, v.v.
            + `session` (AsyncSession): Phiên làm việc với cơ sở dữ liệu.

        - Thực hiện:
            + Truy vấn bản ghi theo ID từ cơ sở dữ liệu.
            + Nếu không tồn tại, trả về lỗi "Không tìm thấy bản ghi".
            + Gán lại các giá trị từ `request` vào bản ghi tương ứng.
            + Ghi lại nội dung XML mới vào file vật lý và cập nhật trong Git.
            + Commit và push thay đổi vào Git repository.

        - Trả về:
            + Phản hồi thành công nếu cập nhật cơ sở dữ liệu và Git thành công.
            + Trả về lỗi nếu xảy ra bất kỳ lỗi nào trong quá trình xử lý.
        """
        obj = await session.get(XmlFile, id)
        if not obj:
            return self.error_response("Không tìm thấy bản ghi")

        for key, value in request.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

        await session.commit()
        workflow_id = await self._enqueue_db_to_git_sync(client)

        return self.success_response("Cập nhật dữ liệu thành công", {"id": obj.id, "workflow_id": workflow_id})

    def extract_metadata(self, xml_dict: dict) -> dict:
        """
        Trích xuất thông tin metadata từ từ điển XML đã được phân tích cú pháp.

        - Tham số:
            + `xml_dict` (dict): Dữ liệu XML sau khi được chuyển đổi từ XML string thành dictionary (thường qua `xmltodict.parse`).

        - Thực hiện:
            + Nếu dictionary không chứa khóa `"root"`, bao bọc toàn bộ dữ liệu trong một khóa `"root"`.
            + Truy cập các thuộc tính trong `root` để lấy các trường: `system_code`, `sub_system_code`, `module_code`, `module`.

        - Trả về:
            + Một dictionary chứa 4 khóa: `"system"`, `"sub_system"`, `"module"`, `"category"`, tương ứng với các giá trị trích xuất được từ XML.
        """
        if "root" not in xml_dict:
            xml_dict = {"root": xml_dict}
        root = xml_dict["root"]
        return {"system": root.get("system_code"), "sub_system": root.get("sub_system_code"), "module": root.get("module_code"), "category": root.get("module")}

    async def import_file(self, files: list[UploadFile] = File(...), session: AsyncSession = None, client: Client = None):
        """
        Nhập khẩu danh sách các file XML vào hệ thống, cho phép cập nhật nếu đã tồn tại hoặc tạo mới nếu chưa có.

        - Các tham số:
            + `files` (list[UploadFile]): Danh sách các file được tải lên (chỉ xử lý các file có phần mở rộng `.xml`).
            + `session` (AsyncSession): Phiên làm việc với cơ sở dữ liệu.

        - Thực hiện:
            + Bỏ qua các file không phải định dạng XML.
            + Đọc nội dung XML và trích xuất metadata từ các trường `system_code`, `sub_system_code`, `module_code`, `module`.
            + Kiểm tra xem file đã tồn tại (dựa trên `filename`) trong cơ sở dữ liệu:
                * Nếu đã tồn tại → cập nhật nội dung và metadata tương ứng.
                * Nếu chưa có → tạo mới bản ghi.
            + Ghi nội dung XML vào Git repository cho cả bản ghi mới và cập nhật.
            + Thu thập kết quả xử lý của từng file (imported, updated, skipped, error).

        - Trả về:
            + Một danh sách phản hồi cho từng file với thông tin: `filename`, `status` (`imported`, `updated`, `skipped`, `error`), và `id` nếu thành công.
        """
        results = []

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

        workflow_id = await self._enqueue_db_to_git_sync(client)
        return {"results": results, "workflow_id": workflow_id}

    async def sync_git_to_db(self, session: AsyncSession):
        """
        Đồng bộ nội dung các file XML từ Git repository vào cơ sở dữ liệu.

        - Các tham số:
            + `session` (AsyncSession): Phiên làm việc với cơ sở dữ liệu.

        - Thực hiện:
            + Duyệt qua toàn bộ file `.xml` trong thư mục Git repository.
            + Với mỗi file:
                * Nếu chưa tồn tại trong DB (dựa trên `filename`) → tạo mới bản ghi và trích xuất metadata.
                * Nếu đã tồn tại nhưng nội dung khác → cập nhật nội dung bản ghi tương ứng.
            + Sau khi xử lý, commit thay đổi vào cơ sở dữ liệu.

        - Trả về:
            + Phản hồi thành công với danh sách các file đã được thêm mới (`[+]`) hoặc cập nhật (`[~]`) trong DB.
        """
        repo_path = get_git_service().repo_path
        synced = []
        for module in MODULE_CONFIGURATION_LIST:
            for fname in os.listdir(repo_path + "/" + module):
                if not fname.endswith(".xml"):
                    continue

                file_path = os.path.join(repo_path, module, fname)
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
        """
        Đồng bộ nội dung các bản ghi XML từ cơ sở dữ liệu vào Git repository.

        - Các tham số:
            + `session` (AsyncSession): Phiên làm việc với cơ sở dữ liệu.

        - Thực hiện:
            + Truy vấn toàn bộ các bản ghi `XmlFile` từ cơ sở dữ liệu.
            + Ghi từng file XML vào hệ thống file (theo `filename` và `system`) thông qua `write_file`.
            + Thêm các file mới ghi vào Git index, commit thay đổi và push lên repository.

        - Trả về:
            + Phản hồi thành công chứa danh sách các file đã ghi vào Git (chỉ tên file).
            + Nếu không có file nào được ghi, commit sẽ không được tạo.
        """
        result = await session.execute(select(XmlFile))
        all_files = result.scalars().all()

        written = []
        git = get_git_service()
        for record in all_files:
            system = (record.system or record.filename.split("_")[0]).lower()
            file_path = git.write_file(content_id=str(record.id), filename=record.filename, content=record.content, system=system)
            written.append(file_path)

        if written:
            git.repo.index.add(written)
            git.repo.index.commit("Đồng bộ từ DB → Git")
            git.push_all()

        return self.success_response("Đã sync DB → Git", {"written": [os.path.basename(p) for p in written]})

    async def get_git_drift(self, session: AsyncSession = None):
        git = get_git_service()
        repo_files = git.list_repo_xml_files()

        result = await session.execute(select(XmlFile))
        records = result.scalars().all()
        db_files = {
            git.build_relative_path(record.filename, (record.system or record.filename.split("_")[0]).lower()): {
                "filename": record.filename,
                "content": (record.content or "").strip(),
            }
            for record in records
        }

        only_in_db = sorted([relative_path for relative_path in db_files if relative_path not in repo_files])
        only_in_git = sorted([relative_path for relative_path in repo_files if relative_path not in db_files])
        content_mismatches = sorted(
            [
                relative_path
                for relative_path in db_files
                if relative_path in repo_files and db_files[relative_path]["content"] != repo_files[relative_path]["content"].strip()
            ]
        )

        db_only_by_content: dict[str, list[str]] = {}
        git_only_by_content: dict[str, list[str]] = {}

        for relative_path in only_in_db:
            content = db_files[relative_path]["content"]
            db_only_by_content.setdefault(content, []).append(relative_path)

        for relative_path in only_in_git:
            content = repo_files[relative_path]["content"].strip()
            git_only_by_content.setdefault(content, []).append(relative_path)

        moves: list[dict[str, str]] = []
        for content, db_paths in db_only_by_content.items():
            git_paths = git_only_by_content.get(content, [])
            pair_count = min(len(db_paths), len(git_paths))
            for index in range(pair_count):
                moves.append(
                    {
                        "from": git_paths[index],
                        "to": db_paths[index],
                        "filename": db_files[db_paths[index]]["filename"],
                    }
                )

        moved_to_paths = {item["to"] for item in moves}
        moved_from_paths = {item["from"] for item in moves}

        db_to_git = {
            "create": [path for path in only_in_db if path not in moved_to_paths],
            "update": content_mismatches,
            "delete": [path for path in only_in_git if path not in moved_from_paths],
            "move": moves,
        }
        git_to_db = {
            "create": [path for path in only_in_git if path not in moved_from_paths],
            "update": content_mismatches,
            "delete": [path for path in only_in_db if path not in moved_to_paths],
            "move": [{"from": item["to"], "to": item["from"], "filename": item["filename"]} for item in moves],
        }

        return self.success_response(
            data={
                "only_in_db": only_in_db,
                "only_in_git": only_in_git,
                "content_mismatches": content_mismatches,
                "db_to_git": db_to_git,
                "git_to_db": git_to_db,
                "summary": {
                    "db_to_git": {
                        "create": len(db_to_git["create"]),
                        "update": len(db_to_git["update"]),
                        "delete": len(db_to_git["delete"]),
                        "move": len(db_to_git["move"]),
                    },
                    "git_to_db": {
                        "create": len(git_to_db["create"]),
                        "update": len(git_to_db["update"]),
                        "delete": len(git_to_db["delete"]),
                        "move": len(git_to_db["move"]),
                    },
                },
                "sync_needed": bool(only_in_db or only_in_git or content_mismatches),
            }
        )

    async def _enqueue_db_to_git_sync(self, client: Client = None):
        if client is None:
            return None
        return await enqueue_git_sync("db_to_git", client)
