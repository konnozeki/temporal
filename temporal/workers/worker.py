import asyncio
from temporalio.client import Client
from temporalio.worker import Worker, WorkflowRunner
from ..workflows.fe_workflow import FeCodeGenerationWorkflow
from ..workflows.be_workflow import BeCodeGenerationWorkflow
from ..workflows.xml_workflow import XMLGenerationWorkflow
from ..activities import all_activities


async def main():
    # Kết nối đến Temporal server
    client = await Client.connect("temporal:7233")

    # Khởi tạo worker và đăng ký workflows
    worker = Worker(
        client,
        task_queue="default",
        workflows=[
            FeCodeGenerationWorkflow,
            BeCodeGenerationWorkflow,
            XMLGenerationWorkflow,
        ],
        activities=all_activities,
    )
    # Bắt đầu worker và lắng nghe các workflow
    print("Worker started...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
