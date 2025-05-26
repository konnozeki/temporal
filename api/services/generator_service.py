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
    workflow_id = data.get("workflow_id")

    try:
        client = await get_client()  # hoặc dùng get_client()
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
        await sio.emit("workflow_status_error", {"error": str(e)}, to=sid)


async def start_raw_generate(template: List[dict], module: str = "FE", client: Client = None, kw={}):
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
    status_enum = (
        {
            "running": "Running",
            "completed": "Completed",
            "failed": "Failed",
            "terminated": "Terminated",
            "cancelled": "Cancelled",
        }.get(status.lower())
        if status
        else None
    )

    query_parts = []
    if status_enum:
        query_parts.append(f"ExecutionStatus = '{status_enum}'")
    query = " and ".join(query_parts) or "WorkflowType != ''"

    iterator = client.list_workflows(
        query=query,
        page_size=page_size,
        next_page_token=next_page_token,
    )

    workflows = []
    async for wf in iterator:
        workflows.append(
            {
                "workflow_id": wf.id,
                "run_id": wf.run_id,
                "status": wf.status.name if wf.status else None,
                "start_time": wf.start_time.isoformat() if wf.start_time else None,
                "close_time": wf.close_time.isoformat() if wf.close_time else None,
                "workflow_type": wf.workflow_type,
            }
        )

    return {"data": workflows, "next_page_token": iterator.next_page_token, "status": "success", "code": 200}


async def get_all_workflows(client: Client, status: str = None, page_size: int = 100):
    all_workflows = []
    next_token = None

    while True:
        result = await get_workflows_by_page(client, page_size=page_size, next_page_token=next_token, status=status)
        all_workflows.extend(result["data"])

        if not result["next_page_token"]:
            break

        next_token = result["next_page_token"]

    return {"message": "Danh sách tất cả workflow", "data": all_workflows, "status": "success", "code": 200}
