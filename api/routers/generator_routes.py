# generator_route.py
from fastapi import APIRouter, File, UploadFile, Depends, Request
from typing import List
from ..services.generator_service import generate, check_status
from ..utils import get_client
from temporalio.client import Client

router = APIRouter()


@router.post("/generate_fe_code/")
async def generate_fe_code(fe_templates: List[UploadFile] = File(...), client: Client = Depends(get_client)):
    return await generate(fe_templates, "FE", client=client)


@router.post("/generate_be_code/")
async def generate_be_code(be_templates: List[UploadFile] = File(...), client: Client = Depends(get_client)):
    return await generate(be_templates, "BE", client=client)


@router.post("/generate_xml/")
async def generate_xml(excel_files: List[UploadFile] = File(...), client: Client = Depends(get_client)):
    return await generate(excel_files, "XML", client=client)


@router.get("/status/{workflow_id}")
async def check(workflow_id: str, client: Client = Depends(get_client)):
    return await check_status(workflow_id, client=client)
