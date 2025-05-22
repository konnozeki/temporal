# api/routes/xml_routes.py
from typing import Dict, Any, List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from api.services import xml_service

router = APIRouter(tags=["xml"])


@router.post("/import/")
async def upload_xml_files(files: List[UploadFile] = File(...), db: AsyncSession = Depends(get_db)):
    return await xml_service.handle_uploaded_xml_files(files, db)


@router.get("/")
async def list_xml_files(db: AsyncSession = Depends(get_db)):
    return await xml_service.list_xml_files(db)


@router.get("/page")
async def list_xml_files_by_page(page=1, size=10, db: AsyncSession = Depends(get_db)):
    return await xml_service.list_xml_files_by_page(db, page=page, size=size)


@router.post("/")
async def store(body: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db)):
    return await xml_service.create_xml_file(body, db)


@router.delete("/delete")
async def delete(idlist: str, db: AsyncSession = Depends(get_db)):
    return await xml_service.delete_record(idlist, db)


@router.put("/{id}")
async def update_xml_file_route(id: int, body: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db)):
    return await xml_service.update_xml_file(id, body, session=db)


@router.get("/{id}")
async def get_xml_by_id(id: int, db: AsyncSession = Depends(get_db)):
    return await xml_service.get_by_id(id, db)


@router.post("/import")
async def import_multiple_xml_files(files: list[UploadFile] = File(...), db: AsyncSession = Depends(get_db)):
    return await xml_service.import_file(files, db)
