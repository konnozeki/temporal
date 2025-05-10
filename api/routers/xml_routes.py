# api/routes/xml_routes.py

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from db.session import get_db
from api.services import xml_service

router = APIRouter(tags=["xml"])


@router.post("/upload/")
async def upload_xml_files(files: List[UploadFile] = File(...), db: AsyncSession = Depends(get_db)):
    return await xml_service.handle_uploaded_xml_files(files, db)


@router.get("/list/")
async def list_xml_files(db: AsyncSession = Depends(get_db)):
    return await xml_service.list_xml_files(db)


@router.get("/{xml_file_id}/versions/")
async def get_versions(xml_file_id: int, db: AsyncSession = Depends(get_db)):
    return await xml_service.get_file_versions(xml_file_id, db)


@router.post("/{xml_file_id}/approve/{version_id}")
async def approve_version(xml_file_id: int, version_id: int, db: AsyncSession = Depends(get_db)):
    return await xml_service.approve_xml_version(xml_file_id, version_id, db)
