import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from config.configuration import TEMPORAL_ADDRESS
from ..workflows.fe_workflow import FeCodeGenerationWorkflow
from ..workflows.be_workflow import BeCodeGenerationWorkflow
from ..workflows.be_deploy_workflow import BeWorkspaceDeployWorkflow
from ..workflows.xml_workflow import XMLGenerationWorkflow
from ..workflows.unit_test_workflow import UnitTestGenerationWorkflow
from ..activities import all_activities
from ..activities.git_job_ops import request_git_sync, set_git_job_completed, set_git_job_failed, set_git_job_running
from ..activities.git_ops import sync_db_to_git, sync_git_to_db
from ..constants import DEFAULT_TASK_QUEUE, GIT_TASK_QUEUE
from ..workflows.git_sync_workflow import GitSyncWorkflow


async def main():
    client = await Client.connect(TEMPORAL_ADDRESS)

    default_worker = Worker(
        client,
        task_queue=DEFAULT_TASK_QUEUE,
        workflows=[
            FeCodeGenerationWorkflow,
            BeCodeGenerationWorkflow,
            BeWorkspaceDeployWorkflow,
            XMLGenerationWorkflow,
            UnitTestGenerationWorkflow,
        ],
        activities=[*all_activities, request_git_sync],
    )

    # Poll git-ops in the main worker process so git sync does not depend on
    # a separate container being up.
    git_worker = Worker(
        client,
        task_queue=GIT_TASK_QUEUE,
        workflows=[GitSyncWorkflow],
        activities=[sync_db_to_git, sync_git_to_db, set_git_job_running, set_git_job_completed, set_git_job_failed],
    )

    print("Workers started...")
    await asyncio.gather(default_worker.run(), git_worker.run())


if __name__ == "__main__":
    asyncio.run(main())
