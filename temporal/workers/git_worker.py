import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from config.configuration import TEMPORAL_ADDRESS
from temporal.activities.git_job_ops import set_git_job_completed, set_git_job_failed, set_git_job_running
from temporal.activities.git_ops import sync_db_to_git, sync_git_to_db
from temporal.constants import GIT_TASK_QUEUE
from temporal.workflows.git_sync_workflow import GitSyncWorkflow


async def main():
    client = await Client.connect(TEMPORAL_ADDRESS)

    worker = Worker(
        client,
        task_queue=GIT_TASK_QUEUE,
        workflows=[GitSyncWorkflow],
        activities=[sync_db_to_git, sync_git_to_db, set_git_job_running, set_git_job_completed, set_git_job_failed],
    )
    print("Git worker started...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
