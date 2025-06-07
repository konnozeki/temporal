# from fastapi import APIRouter, HTTPException, Depends
# from sqlalchemy.orm import Session
# from db.session import get_db
# from ..services import git_service

# router = APIRouter(prefix="/git", tags=["Git"])


# @router.post("/init/")
# def init_git_repo(repo_name: str, db: Session = Depends(get_db)):
#     return git_service.init_repository(repo_name)


# @router.post("/commit/")
# def commit_approved_xml(db: Session = Depends(get_db)):
#     return git_service.commit_approved_files(db)


# @router.post("/push/")
# def push_to_remote(db: Session = Depends(get_db)):
#     return git_service.push_to_remote(db)
