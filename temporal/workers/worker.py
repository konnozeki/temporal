import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from ..workflows.fe_workflow import FeCodeGenerationWorkflow
from ..workflows.be_workflow import BeCodeGenerationWorkflow
from ..workflows.xml_workflow import XMLGenerationWorkflow


async def main():
    # Kết nối đến Temporal server
    client = await Client.connect("localhost:7233")

    # Khởi tạo worker và đăng ký workflows
    worker = Worker(
        client,
        task_queue="default",
        workflows=[
            FeCodeGenerationWorkflow,
            BeCodeGenerationWorkflow,
            XMLGenerationWorkflow,
        ],
    )
    # Bắt đầu worker và lắng nghe các workflow
    print("Worker started...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
