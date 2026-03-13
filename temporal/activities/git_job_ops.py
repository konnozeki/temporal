from temporalio import activity

from api.services.git_job_service import mark_git_job_completed, mark_git_job_failed, mark_git_job_running
from api.services.git_sync_service import enqueue_git_sync


@activity.defn
async def request_git_sync(direction: str) -> str:
    return await enqueue_git_sync(direction)


@activity.defn
async def set_git_job_running(workflow_id: str):
    await mark_git_job_running(workflow_id)


@activity.defn
async def set_git_job_completed(workflow_id: str):
    await mark_git_job_completed(workflow_id)


@activity.defn
async def set_git_job_failed(workflow_id: str, error: str):
    await mark_git_job_failed(workflow_id, error)
