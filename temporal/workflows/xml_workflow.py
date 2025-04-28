# temporal/workflows/xml_generator.py
from temporalio import workflow
from temporal.activities.xml_generator import excel_to_xml


@workflow.defn
class XMLGenerationWorkflow:

    @workflow.run
    async def run(self, excel_data: str):
        # Gọi activity chuyển đổi Excel sang XML
        xml_data = await workflow.execute_activity(excel_to_xml, excel_data)
        return xml_data
