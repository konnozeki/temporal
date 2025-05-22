from temporalio import workflow
from temporalio.common import RetryPolicy

from ..activities.xml_generator import generate_xml
import base64
import zipfile
import io
from datetime import timedelta
from db.session import async_session  # hoặc wherever bạn khai DB session
import os
from pathlib import Path
from sqlalchemy import select
from ..activities.db_writer import save_generated_xml
import asyncio


@workflow.defn(sandboxed=False)
class XMLGenerationWorkflow:

    @workflow.run
    async def run(self, template_contents, kw={}):
        # Tạo buffer zip
        zip_buffer = io.BytesIO()
        try:
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file in template_contents:
                    content = bytes(file["content"])
                    if not isinstance(content, bytes):
                        raise ValueError("File content must be bytes")

                    xml_dict = await workflow.execute_activity(
                        generate_xml,
                        args=[content, kw],
                        start_to_close_timeout=timedelta(seconds=30),
                    )

                    await workflow.execute_activity(
                        save_generated_xml,
                        args=[xml_dict, kw.get("module", "categories")],
                        start_to_close_timeout=timedelta(seconds=60),
                    )
                    for model_name, xml_string in xml_dict.items():
                        # Tạo tên file cho các tệp cần nén
                        zip_file.writestr(f"xml/{model_name}_schema.xml", xml_string)

            # Lấy nội dung zip và trả về kết quả
            zip_buffer.seek(0)
            zip_content = zip_buffer.getvalue()
            zip_b64 = base64.b64encode(zip_content).decode("utf-8")

            # Logging thông tin thành công
            workflow.logger.info("Workflow completed successfully")

            return {"zip_content": zip_b64}

        except Exception as e:
            workflow.logger.error(f"Error in workflow execution: {e}")
            raise
