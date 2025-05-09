from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from db.session import get_db
from ..services import xml_service

router = APIRouter(prefix="/xml", tags=["XML"])


@router.post("/upload/")
async def upload_xml_files(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    return await xml_service.handle_uploaded_xml_files(files, db)


@router.get("/list/")
def list_xml_files(db: Session = Depends(get_db)):
    return xml_service.list_xml_files(db)


@router.get("/{xml_file_id}/versions/")
def get_versions(xml_file_id: int, db: Session = Depends(get_db)):
    return xml_service.get_file_versions(xml_file_id, db)


@router.post("/{xml_file_id}/approve/{version_id}")
def approve_version(xml_file_id: int, version_id: int, db: Session = Depends(get_db)):
    return xml_service.approve_xml_version(xml_file_id, version_id, db)
