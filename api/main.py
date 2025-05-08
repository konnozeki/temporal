# main.py
import base64
from io import BytesIO
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from temporalio.client import Client
from .workflow_status import set_status, get_status
from temporal.workflows.fe_workflow import FeCodeGenerationWorkflow
from temporal.workflows.be_workflow import BeCodeGenerationWorkflow
from temporal.workflows.xml_workflow import XMLGenerationWorkflow
import os
import uuid
from contextlib import asynccontextmanager
from typing import List


CONFIGURATION = {
    "FE": {"workflow": FeCodeGenerationWorkflow, "extension": "js"},
    "BE": {"workflow": BeCodeGenerationWorkflow, "extension": "py"},
    "XML": {"workflow": XMLGenerationWorkflow, "extension": "xml"},
}
client: Client = None  # Global biến


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = await Client.connect("temporal:7233")
    print("✅ Temporal client connected.")
    yield
    await client.close()
    print("🛑 Temporal client closed.")


app = FastAPI(lifespan=lifespan)


# API check status của workflow
@app.get("/status/{workflow_id}")
async def check_status(workflow_id: str):
    status = get_status(workflow_id)
    return {"workflow_id": workflow_id, "status": status}


async def generate(template: List[UploadFile] = File(...), module: str = "FE", **kw):
    if module not in CONFIGURATION.keys():
        raise HTTPException(status_code=400, detail="Invalid module")

    if not template or len(template) == 0:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # Đọc nội dung các file upload
    template_contents = []
    for file in template:
        content = await file.read()
        template_contents.append(
            {
                "filename": file.filename,
                "content": content,
            }
        )

    # Tạo workflow ID duy nhất
    workflow_id = f"{module}-{uuid.uuid4().hex[:8]}"
    set_status(workflow_id, "processing")

    # Gọi workflow
    try:
        result = await client.execute_workflow(
            CONFIGURATION[module](**kw)["workflow"].run,
            template_contents,
            id=workflow_id,
            task_queue="default",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing workflow: {str(e)}")

    # Lấy dữ liệu zip từ kết quả
    zip_b64 = result.get("zip_content")
    if not zip_b64:
        raise HTTPException(status_code=500, detail="Workflow completed but no zip_content returned")

    # Trả về file zip
    zip_bytes = base64.b64decode(zip_b64)
    return StreamingResponse(
        content=BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="result.zip"'},
    )


@app.post("/generate_fe_code/")
async def generate_fe_code(fe_templates: List[UploadFile] = File(...)):
    return await generate(fe_templates, "FE")


@app.post("/generate_be_code/")
async def generate_be_code(be_templates: List[UploadFile] = File(...)):
    return await generate(be_templates, "BE")


# API generate XML từ Excel
@app.post("/generate_xml/")
async def generate_xml(excel_files: List[UploadFile] = File(...)):
    return await generate(excel_files, "XML")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
