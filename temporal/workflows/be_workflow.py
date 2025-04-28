# temporal/workflows/be_generator.py
from temporalio import workflow
from temporal.activities.be_generator import generate_be_code


@workflow.defn
class BeCodeGenerationWorkflow:

    @workflow.run
    async def run(self, be_template: str):
        # Gọi activity để sinh mã backend
        be_code = await workflow.execute_activity(generate_be_code, be_template)
        return be_code
