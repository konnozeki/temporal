import base64
from io import BytesIO
from fastapi import UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from temporalio.client import Client
from ..workflow_status import set_status, get_status
from temporal.workflows.fe_workflow import FeCodeGenerationWorkflow
from temporal.workflows.be_workflow import BeCodeGenerationWorkflow
from temporal.workflows.xml_workflow import XMLGenerationWorkflow
from temporal.workflows.unit_test_workflow import UnitTestGenerationWorkflow
import uuid
from typing import List, Dict
from ..utils import sio
import asyncio
from temporalio.client import WorkflowHandle
from ..utils import get_client
import json

CONFIGURATION = {
    "FE": {"workflow": FeCodeGenerationWorkflow, "extension": "js"},
    "BE": {"workflow": BeCodeGenerationWorkflow, "extension": "py"},
    "XML": {"workflow": XMLGenerationWorkflow, "extension": "xml"},
    "UT": {"workflow": UnitTestGenerationWorkflow, "extension": "zip"},
}


@sio.event
async def workflow_status(sid, data):
    """
    Lắng nghe sự kiện `workflow_status` từ client và gửi cập nhật trạng thái của các workflow theo thời gian thực.

    - Các tham số:
        + `sid`: Session ID của client kết nối qua Socket.IO.
        + `data` (dict): Dữ liệu từ client gửi lên, yêu cầu phải chứa khóa `workflow_ids` là danh sách các workflow ID hợp lệ.
    - Ví dụ `data` đầu vào:
        {
            "workflow_ids": ["abc123", "xyz456"]
        }
    - Thực hiện:
        + Kiểm tra định dạng và nội dung của `workflow_ids`.
        + Với mỗi workflow ID:
            * Gọi `describe()` liên tục để lấy thông tin trạng thái của workflow.
            * Gửi sự kiện `workflow_status_update` về cho client với các thông tin: trạng thái, thời gian bắt đầu, kết thúc, loại workflow...
            * Dừng khi workflow kết thúc (COMPLETED, FAILED, TERMINATED, hoặc CANCELED).
        + Tất cả workflows được theo dõi song song bằng `asyncio.gather`.

    - Trả về:
        + Gửi liên tục các sự kiện `workflow_status_update` cho client theo từng workflow.
        + Nếu có lỗi xảy ra trong bất kỳ workflow nào, gửi sự kiện `workflow_status_error` kèm chi tiết lỗi.
    """
    workflow_ids = data.get("workflow_ids", [])

    if not isinstance(workflow_ids, list) or not workflow_ids:
        await sio.emit("workflow_status_error", {"error": "Danh sách workflow_ids không hợp lệ"}, to=sid)
        return

    try:
        client = await get_client()

        async def track_workflow(workflow_id):
            try:
                handle = client.get_workflow_handle(workflow_id)

                while True:
                    info = await handle.describe()
                    await sio.emit(
                        "workflow_status_update",
                        {
                            "workflow_id": workflow_id,
                            "status": info.status.name,
                            "history_length": info.history_length,
                            "close_time": info.close_time.isoformat() if info.close_time else None,
                            "start_time": info.start_time.isoformat() if info.start_time else None,
                            "workflow_type": info.workflow_type,
                        },
                        to=sid,
                    )

                    if info.status.name in ("COMPLETED", "FAILED", "TERMINATED", "CANCELED"):
                        break

                    await asyncio.sleep(2)

            except Exception as e:
                await sio.emit("workflow_status_error", {"workflow_id": workflow_id, "error": str(e)}, to=sid)

        # Chạy tất cả workflows song song
        await asyncio.gather(*(track_workflow(wid) for wid in workflow_ids))

    except Exception as e:
        await sio.emit("workflow_status_error", {"error": str(e)}, to=sid)


async def start_raw_generate(template: List[dict], module: str = "FE", client: Client = None, kw={}):
    """
    Khởi động một workflow xử lý sinh dữ liệu XML từ danh sách template đầu vào.

    - Các tham số:
        + `template` (List[dict]): Danh sách các dictionary, mỗi dict chứa `filename` và `content` (dạng chuỗi).
        + `module` (str): Tên module cần xử lý, mặc định là `"FE"`. Phải nằm trong `CONFIGURATION`.
        + `client` (Client): Đối tượng client kết nối tới Temporal để start workflow.
        + `kw` (dict): Tham số phụ (tùy chọn) sẽ được truyền vào workflow dưới dạng context.

    - Thực hiện:
        + Kiểm tra hợp lệ của `module` và `template`.
        + Chuẩn hóa dữ liệu đầu vào (mã hóa content thành bytes).
        + Tạo `workflow_id` mới dựa trên module và UUID ngắn.
        + Đánh dấu trạng thái `processing` ban đầu.
        + Gọi `start_workflow` trên Temporal client để khởi động workflow với dữ liệu đã chuẩn hóa.

    - Trả về:
        + Dictionary chứa mã thành công, thông điệp, và `workflow_id` nếu khởi tạo thành công.

    - Lỗi:
        + Trả về mã lỗi 400 nếu thiếu dữ liệu hoặc module không hợp lệ.
        + Trả về mã lỗi 500 nếu không thể khởi động workflow.
    """
    if kw is None:
        kw = {}

    if module not in CONFIGURATION:
        raise HTTPException(status_code=400, detail="Invalid module")

    if not template:
        raise HTTPException(status_code=400, detail="No list uploaded")

    template_contents = []
    for item in template:
        filename = item.get("filename")
        content = item.get("content")
        if not filename or not content:
            raise HTTPException(status_code=400, detail="Missing filename or content in item")

        template_contents.append({"filename": filename, "content": content.encode("utf-8")})

    workflow_id = f"{module}-{uuid.uuid4().hex[:8]}"
    set_status(workflow_id, "processing")

    try:
        handle: WorkflowHandle = await client.start_workflow(
            CONFIGURATION[module]["workflow"].run,
            args=[template_contents, kw],
            id=workflow_id,
            task_queue="default",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed to start: {str(e)}")

    return {
        "code": 200,
        "status": "success",
        "message": "Tạo workflow thành công",
        "data": {"workflow_id": workflow_id},
    }


async def start_generate(template: List[UploadFile], module: str = "FE", client: Client = None, kw={}):
    """
    Khởi động một workflow xử lý sinh dữ liệu XML từ danh sách file được tải lên.

    - Các tham số:
        + `template` (List[UploadFile]): Danh sách các file được upload (thường từ form-data).
        + `module` (str): Tên module cần xử lý, mặc định là `"FE"`. Phải nằm trong `CONFIGURATION`.
        + `client` (Client): Đối tượng Temporal client để khởi tạo workflow.
        + `kw` (dict): Tham số phụ truyền vào workflow dưới dạng context.

    - Thực hiện:
        + Kiểm tra hợp lệ của `module` và danh sách file `template`.
        + Đọc toàn bộ nội dung các file và chuẩn hóa về danh sách dictionary gồm `filename` và `content` (dạng bytes).
        + Tạo một `workflow_id` mới dựa trên module và UUID.
        + Ghi trạng thái `processing` cho workflow.
        + Gọi `start_workflow` (không đồng bộ kết quả) để khởi tạo workflow trên Temporal.

    - Trả về:
        + Dictionary phản hồi thành công, bao gồm mã, trạng thái, thông điệp và `workflow_id`.

    - Lỗi:
        + Trả về mã lỗi 400 nếu thiếu file hoặc module không hợp lệ.
        + Trả về mã lỗi 500 nếu khởi động workflow thất bại.
    """
    if module not in CONFIGURATION:
        raise HTTPException(status_code=400, detail="Invalid module")

    if not template:
        raise HTTPException(status_code=400, detail="No files uploaded")

    template_contents = []
    for file in template:
        content = await file.read()
        template_contents.append({"filename": file.filename, "content": content})

    workflow_id = f"{module}-{uuid.uuid4().hex[:8]}"
    set_status(workflow_id, "processing")

    try:
        # KHÁC Ở ĐÂY — dùng start_workflow thay vì execute_workflow
        handle: WorkflowHandle = await client.start_workflow(
            CONFIGURATION[module]["workflow"].run,
            args=[template_contents, kw],
            id=workflow_id,
            task_queue="default",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed to start: {str(e)}")

    return {
        "code": 200,
        "status": "success",
        "message": "Tạo workflow thành công",
        "data": {"workflow_id": workflow_id},
    }


async def download_result(workflow_id: str, client: Client):
    """
    Tải xuống kết quả đầu ra từ một workflow đã hoàn thành dưới dạng file ZIP.

    - Các tham số:
        + `workflow_id` (str): ID của workflow cần truy xuất kết quả.
        + `client` (Client): Đối tượng Temporal client để lấy handle workflow.

    - Thực hiện:
        + Lấy handle của workflow thông qua `client.get_workflow_handle`.
        + Chờ workflow hoàn tất bằng `handle.result()`.
        + Kiểm tra xem kết quả có trường `zip_content` (dưới dạng base64) không.
        + Giải mã nội dung base64 thành bytes và trả về dưới dạng `StreamingResponse` với định dạng ZIP.

    - Trả về:
        + File ZIP chứa kết quả, gửi dưới dạng response tải xuống (`Content-Disposition: attachment`).

    - Lỗi:
        + Trả về mã lỗi 500 nếu không lấy được kết quả hoặc `zip_content` không tồn tại.
    """
    try:
        handle = client.get_workflow_handle(workflow_id)
        result = await handle.result()  # Chờ workflow hoàn thành và lấy kết quả

        zip_b64 = result.get("zip_content")
        if not zip_b64:
            raise HTTPException(status_code=500, detail="Workflow completed but no zip_content returned")

        zip_bytes = base64.b64decode(zip_b64)
        return StreamingResponse(content=BytesIO(zip_bytes), media_type="application/zip", headers={"Content-Disposition": 'attachment; filename="result.zip"'})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_workflows_by_page(client: Client, page_size: int = 50, next_page_token: str = None, status: str = None):
    """
    Lấy danh sách workflow từ Temporal theo phân trang, với tùy chọn lọc theo trạng thái.

    - Các tham số:
        + `client` (Client): Đối tượng Temporal client để truy vấn workflow.
        + `page_size` (int): Số lượng workflow mỗi trang. Mặc định là 50.
        + `next_page_token` (str): Token phân trang dùng để lấy trang tiếp theo. Mặc định là None.
        + `status` (str): Trạng thái của workflow để lọc (chấp nhận: "running", "completed", "failed", "terminated", "cancelled"). Mặc định là None.

    - Thực hiện:
        + Xây dựng câu truy vấn dựa trên trạng thái nếu có.
        + Sử dụng `client.list_workflows` để duyệt từng workflow theo trang.
        + Lấy các trường thông tin cơ bản: `workflow_id`, `run_id`, `status`, `start_time`, `close_time`, `history_length`, `workflow_type`.

    - Trả về:
        + Dictionary chứa:
            * `data`: Danh sách các workflow phù hợp.
            * `next_page_token`: Token để truy vấn trang tiếp theo (nếu còn).
            * `status`: Trạng thái phản hồi (luôn `"success"` nếu không lỗi).
            * `code`: Mã phản hồi (luôn `200` nếu thành công).

    - Lỗi:
        + Trường hợp không truy vấn được workflow sẽ raise exception từ `Temporal client` (cần được bắt tại nơi gọi nếu cần xử lý).
    """
    status_enum = {"running": "Running", "completed": "Completed", "failed": "Failed", "terminated": "Terminated", "cancelled": "Cancelled"}.get(status.lower()) if status else None

    query_parts = []
    if status_enum:
        query_parts.append(f"ExecutionStatus = '{status_enum}'")
    query = " and ".join(query_parts) or "WorkflowType != ''"

    iterator = client.list_workflows(query=query, page_size=page_size, next_page_token=next_page_token)

    workflows = []
    async for wf in iterator:
        workflows.append(
            {
                "workflow_id": wf.id,
                "run_id": wf.run_id,
                "status": wf.status.name if wf.status else None,
                "start_time": wf.start_time.isoformat() if wf.start_time else None,
                "close_time": wf.close_time.isoformat() if wf.close_time else None,
                "history_length": wf.history_length,
                "workflow_type": wf.workflow_type,
            }
        )

    return {"data": workflows, "next_page_token": iterator.next_page_token, "status": "success", "code": 200}


async def get_all_workflows(client: Client, status: str = None, page_size: int = 100):
    """
    Truy vấn toàn bộ danh sách workflow từ Temporal, với tùy chọn lọc theo trạng thái.

    - Các tham số:
        + `client` (Client): Đối tượng Temporal client dùng để truy xuất workflow.
        + `status` (str): Trạng thái để lọc workflow (ví dụ: "running", "completed", "failed", "terminated", "cancelled"). Mặc định là None (lấy tất cả).
        + `page_size` (int): Số lượng workflow mỗi lần truy vấn (theo trang). Mặc định là 100.

    - Thực hiện:
        + Gọi `get_workflows_by_page` nhiều lần để lấy toàn bộ workflow theo từng trang.
        + Lặp cho đến khi không còn `next_page_token`.
        + Tích lũy kết quả vào danh sách `all_workflows`.

    - Trả về:
        + Dictionary chứa:
            * `message`: Mô tả kết quả.
            * `data`: Danh sách tất cả workflow được lấy.
            * `status`: Chuỗi `"success"`.
            * `code`: Mã phản hồi (200 nếu thành công).

    - Ghi chú:
        + Hàm này sẽ lấy toàn bộ kết quả nên có thể mất thời gian nếu workflow nhiều.
        + Nên giới hạn hoặc phân trang lại ở phía frontend nếu dữ liệu trả về quá lớn.
    """

    all_workflows = []
    next_token = None

    while True:
        result = await get_workflows_by_page(client, page_size=page_size, next_page_token=next_token, status=status)
        all_workflows.extend(result["data"])

        if not result["next_page_token"]:
            break

        next_token = result["next_page_token"]

    return {"message": "Danh sách tất cả workflow", "data": all_workflows, "status": "success", "code": 200}
