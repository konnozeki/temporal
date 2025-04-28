# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from temporalio.client import Client
from api.workflow_status import set_status, get_status
from temporal.workflows.fe_workflow import FeCodeGenerationWorkflow
from temporal.workflows.be_workflow import BeCodeGenerationWorkflow
from temporal.workflows.xml_workflow import XMLGenerationWorkflow
import os
import uuid
from contextlib import asynccontextmanager
from typing import List
from api.utils import save_multiple_files


OUTPUT_FOLDER = "./outputs"
CONFIGURATION = {
    "FE": {"workflow": FeCodeGenerationWorkflow, "extension": "js"},
    "BE": {"workflow": BeCodeGenerationWorkflow, "extension": "py"},
    "XML": {"workflow": XMLGenerationWorkflow, "extension": "xml"},
}
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

client: Client = None  # Global biến


# Helper function: ghi nội dung vào file
async def save_to_file(content: str, extension: str):
    filename = f"{uuid.uuid4().hex}.{extension}"
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = await Client.connect("localhost:7233")
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


async def generate(template: List[UploadFile] = File(...), module="FE"):
    if not (module in CONFIGURATION.keys()):
        raise HTTPException(status_code=400, detail="Invalid module")
    if not template or len(template) == 0:
        raise HTTPException(status_code=400, detail="No files uploaded")

    template_contents = []
    for file in template:
        content = await file.read()
        template_contents.append(
            {
                "filename": file.filename,
                "content": content,
            }
        )
    workflow_id = f"{module}-{uuid.uuid4().hex[:8]}"
    set_status(workflow_id, "processing")

    try:
        result = await client.execute_workflow(
            CONFIGURATION[module]["workflow"].run,
            template_contents,
            id=workflow_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing workflow: {str(e)}")

    # result bây giờ là dict {filename: content}
    zip_file_path = await save_multiple_files(result, CONFIGURATION[module]["extension"])  # save to file với định dạng JS
    set_status(workflow_id, "done")

    return FileResponse(
        zip_file_path,
        media_type="application/zip",
        filename=os.path.basename(zip_file_path),
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
