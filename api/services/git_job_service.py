from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db.models import GitJob
from db.session import async_session

ACTIVE_GIT_JOB_STATUSES = {"queued", "running"}


async def reserve_git_job(direction: str, workflow_id: str) -> str:
    async with async_session() as session:
        result = await session.execute(select(GitJob).where(GitJob.direction == direction))
        job = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if job is None:
            job = GitJob(direction=direction, workflow_id=workflow_id, status="queued")
            session.add(job)
        else:
            job.workflow_id = workflow_id
            job.status = "queued"
            job.last_error = None
            job.started_at = None
            job.completed_at = None
            job.requested_at = now
            job.updated_at = now

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            result = await session.execute(select(GitJob).where(GitJob.direction == direction))
            existing = result.scalar_one_or_none()
            if existing is not None:
                return existing.workflow_id
            raise

    return workflow_id


async def mark_git_job_running(workflow_id: str):
    await _update_git_job(
        workflow_id,
        status="running",
        started_at=datetime.now(timezone.utc),
        last_error=None,
    )


async def mark_git_job_completed(workflow_id: str):
    now = datetime.now(timezone.utc)
    await _update_git_job(
        workflow_id,
        status="completed",
        completed_at=now,
        last_error=None,
    )


async def mark_git_job_failed(workflow_id: str, error: str):
    await _update_git_job(
        workflow_id,
        status="failed",
        completed_at=datetime.now(timezone.utc),
        last_error=error,
    )


async def get_active_git_job(direction: str) -> GitJob | None:
    async with async_session() as session:
        result = await session.execute(select(GitJob).where(GitJob.direction == direction))
        job = result.scalar_one_or_none()
        if job is None or job.status not in ACTIVE_GIT_JOB_STATUSES:
            return None
        return job


async def get_git_job(direction: str) -> GitJob | None:
    async with async_session() as session:
        result = await session.execute(select(GitJob).where(GitJob.direction == direction))
        return result.scalar_one_or_none()


async def _update_git_job(workflow_id: str, **fields):
    async with async_session() as session:
        result = await session.execute(select(GitJob).where(GitJob.workflow_id == workflow_id))
        job = result.scalar_one_or_none()
        if job is None:
            return

        for key, value in fields.items():
            setattr(job, key, value)
        job.updated_at = datetime.now(timezone.utc)
        await session.commit()
