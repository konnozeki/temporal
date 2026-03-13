# api/routes/xml_routes.py
from typing import Dict, Any, List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client
from db.session import get_db
from api.services.xml_service import XmlService
from api.services.git_sync_service import enqueue_git_sync
from api.utils import get_client

router = APIRouter(tags=["xml"])
xml_service = XmlService()


@router.post("/import/")
async def upload_xml_files(files: List[UploadFile] = File(...), db: AsyncSession = Depends(get_db), client: Client = Depends(get_client)):
    return await xml_service.handle_uploaded_xml_files(files, db, client=client)


@router.get("/")
async def list_xml_files(db: AsyncSession = Depends(get_db)):
    return await xml_service.list_xml_files(db)


@router.get("/page")
async def list_xml_files_by_page(page=1, size=10, idlist="", db: AsyncSession = Depends(get_db)):
    return await xml_service.list_xml_files_by_page(page=page, size=size, idlist=idlist, session=db)


@router.post("/")
async def store(body: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db), client: Client = Depends(get_client)):
    return await xml_service.create_xml_file(body, session=db, client=client)


@router.delete("/delete")
async def delete(idlist: str, db: AsyncSession = Depends(get_db), client: Client = Depends(get_client)):
    result = await xml_service.delete_record(idlist, session=db)
    if result.get("status") == "success":
        result["data"] = {"deleted_ids": result.get("data"), "workflow_id": await enqueue_git_sync("db_to_git", client)}
    return result


@router.put("/{id}")
async def update_xml_file_route(id: int, body: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db), client: Client = Depends(get_client)):
    return await xml_service.update_xml_file(id, body, session=db, client=client)


@router.get("/{id}")
async def get_xml_by_id(id: int, db: AsyncSession = Depends(get_db)):
    return await xml_service.get_by_id(id, session=db)


@router.post("/import")
async def import_multiple_xml_files(files: list[UploadFile] = File(...), db: AsyncSession = Depends(get_db), client: Client = Depends(get_client)):
    return await xml_service.import_file(files, session=db, client=client)


@router.post("/sync/git")
async def sync_git(client: Client = Depends(get_client)):
    workflow_id = await enqueue_git_sync("git_to_db", client)
    return {"status": "accepted", "code": 202, "data": {"workflow_id": workflow_id, "direction": "git_to_db"}}


@router.post("/sync/db")
async def sync_db(client: Client = Depends(get_client)):
    workflow_id = await enqueue_git_sync("db_to_git", client)
    return {"status": "accepted", "code": 202, "data": {"workflow_id": workflow_id, "direction": "db_to_git"}}
