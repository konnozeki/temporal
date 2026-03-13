from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client

from api.services.git_job_service import get_git_job
from api.services.git_service import get_git_service
from api.services.git_sync_service import enqueue_git_sync
from api.services.xml_service import XmlService
from api.utils import get_client
from db.session import get_db

router = APIRouter(tags=["git"])
xml_service = XmlService()


@router.get("/status")
async def git_status():
    git = get_git_service()
    return {"status": "success", "code": 200, "data": git.get_status()}


@router.get("/drift")
async def git_drift(db: AsyncSession = Depends(get_db)):
    return await xml_service.get_git_drift(session=db)


@router.get("/preview")
async def git_preview(direction: str = "db_to_git", db: AsyncSession = Depends(get_db)):
    if direction not in {"db_to_git", "git_to_db"}:
        return {"status": "error", "code": 400, "message": "direction must be db_to_git or git_to_db"}

    result = await xml_service.get_git_drift(session=db)
    data = result.get("data", {})
    preview = data.get(direction, {})
    summary = data.get("summary", {}).get(direction, {})
    return {
        "status": "success",
        "code": 200,
        "data": {
            "direction": direction,
            "preview": preview,
            "summary": summary,
            "sync_needed": bool(sum(summary.values())) if summary else data.get("sync_needed", False),
        },
    }


@router.get("/jobs/{direction}")
async def git_job_status(direction: str):
    if direction not in {"db_to_git", "git_to_db"}:
        return {"status": "error", "code": 400, "message": "direction must be db_to_git or git_to_db"}

    job = await get_git_job(direction)
    if job is None:
        return {"status": "success", "code": 200, "data": None}

    return {
        "status": "success",
        "code": 200,
        "data": {
            "direction": job.direction,
            "workflow_id": job.workflow_id,
            "status": job.status,
            "last_error": job.last_error,
            "requested_at": job.requested_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "updated_at": job.updated_at,
        },
    }


@router.post("/sync")
async def trigger_git_sync(
    body: dict = Body(default={"direction": "db_to_git"}),
    client: Client = Depends(get_client),
):
    direction = body.get("direction", "db_to_git")
    if direction not in {"db_to_git", "git_to_db"}:
        return {"status": "error", "code": 400, "message": "direction must be db_to_git or git_to_db"}

    workflow_id = await enqueue_git_sync(direction, client)
    return {"status": "accepted", "code": 202, "data": {"workflow_id": workflow_id, "direction": direction}}
