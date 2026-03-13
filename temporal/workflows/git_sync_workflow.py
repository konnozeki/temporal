from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from temporal.activities.git_job_ops import set_git_job_completed, set_git_job_failed, set_git_job_running
from temporal.activities.git_ops import sync_db_to_git, sync_git_to_db
from temporal.constants import GIT_TASK_QUEUE


@workflow.defn(name="git-sync-workflow", sandboxed=False)
class GitSyncWorkflow:
    @workflow.run
    async def run(self, direction: str, workflow_id: str):
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=2),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(minutes=1),
            maximum_attempts=5,
        )

        await workflow.execute_activity(
            set_git_job_running,
            workflow_id,
            start_to_close_timeout=timedelta(seconds=30),
            task_queue=GIT_TASK_QUEUE,
        )

        try:
            if direction == "db_to_git":
                result = await workflow.execute_activity(
                    sync_db_to_git,
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=retry_policy,
                    task_queue=GIT_TASK_QUEUE,
                )
            elif direction == "git_to_db":
                result = await workflow.execute_activity(
                    sync_git_to_db,
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=retry_policy,
                    task_queue=GIT_TASK_QUEUE,
                )
            else:
                raise ValueError(f"Unsupported git sync direction: {direction}")

            await workflow.execute_activity(
                set_git_job_completed,
                workflow_id,
                start_to_close_timeout=timedelta(seconds=30),
                task_queue=GIT_TASK_QUEUE,
            )
            return result
        except Exception as exc:
            await workflow.execute_activity(
                set_git_job_failed,
                args=[workflow_id, str(exc)],
                start_to_close_timeout=timedelta(seconds=30),
                task_queue=GIT_TASK_QUEUE,
            )
            raise
