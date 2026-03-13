import uuid

from temporalio.client import Client

from config.configuration import TEMPORAL_ADDRESS
from temporal.constants import GIT_TASK_QUEUE
from .git_job_service import mark_git_job_failed, reserve_git_job

GIT_SYNC_WORKFLOW_NAME = "git-sync-workflow"


async def enqueue_git_sync(direction: str, client: Client | None = None) -> str:
    workflow_id = f"git-sync-{direction}-{uuid.uuid4().hex[:12]}"
    reserved_workflow_id = await reserve_git_job(direction, workflow_id)
    if reserved_workflow_id != workflow_id:
        return reserved_workflow_id

    owns_client = client is None
    if client is None:
        client = await Client.connect(TEMPORAL_ADDRESS)

    try:
        await client.start_workflow(
            GIT_SYNC_WORKFLOW_NAME,
            args=[direction, workflow_id],
            id=workflow_id,
            task_queue=GIT_TASK_QUEUE,
        )
        return workflow_id
    except Exception as exc:
        await mark_git_job_failed(workflow_id, str(exc))
        raise
    finally:
        if owns_client and client is not None:
            await client.close()
