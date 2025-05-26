# generator_route.py
from fastapi import APIRouter, File, UploadFile, Depends, Request, Body
from typing import List, Dict
from ..services.generator_service import start_generate, download_result, get_all_workflows, get_workflows_by_page, start_raw_generate
from ..utils import get_client
from temporalio.client import Client

router = APIRouter()


@router.post("/generate_fe/")
async def generate_fe(templates: List[UploadFile] = File(...), client: Client = Depends(get_client)):
    return await start_generate(templates, "FE", client=client)


@router.post("/generate_be/")
async def generate_be(templates: List[UploadFile] = File(...), client: Client = Depends(get_client)):
    return await start_generate(templates, "BE", client=client)


@router.post("/generate_ut/")
async def generate_be(templates: List[UploadFile] = File(...), client: Client = Depends(get_client)):
    return await start_generate(templates, "UT", client=client)


@router.post("/generate_raw_fe/")
async def generate_raw_fe(templates: List[dict] = Body(...), client: Client = Depends(get_client)):
    return await start_raw_generate(templates, "FE", client=client)


@router.post("/generate_raw_be/")
async def generate_raw_be(templates: List[dict] = Body(...), client: Client = Depends(get_client)):
    return await start_raw_generate(templates, "BE", client=client)


@router.post("/generate_raw_ut/")
async def generate_raw_be(templates: List[dict] = Body(...), client: Client = Depends(get_client)):
    return await start_raw_generate(templates, "UT", client=client)


@router.post("/generate_xml/")
async def generate_xml(excel_files: List[UploadFile] = File(...), client: Client = Depends(get_client), request: Request = None):
    form = await request.form()
    kwargs = dict(form)
    kwargs = {k: v for k, v in kwargs.items() if k not in ["excel_files", "client"]}
    return await start_generate(excel_files, "XML", client=client, kw=kwargs)


@router.get("/download/{workflow_id}")
async def download_file(workflow_id: str, client=Depends(get_client)):
    return await download_result(workflow_id, client=client)


@router.get("/workflows")
async def list_all_temporal(client: Client = Depends(get_client), status: str = None):
    return await get_all_workflows(client, status=status)


@router.get("/workflows/page")
async def list_temporal_by_page(client: Client = Depends(get_client), page_size: int = 50, next_token: str = None, status: str = None):
    return await get_workflows_by_page(client, page_size=page_size, next_page_token=next_token, status=status)
