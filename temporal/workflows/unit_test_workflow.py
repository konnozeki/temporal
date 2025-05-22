import io
import zipfile
import base64
import xmltodict
from temporalio import workflow
from datetime import timedelta
from ..activities.fe_generator import generate_column_setting, generate_i18n, generate_menu, generate_service, generate_configuration
import asyncio


@workflow.defn(sandboxed=False)
class UnitTestGenerationWorkflow:
    def __init__(self, **kw):
        pass

    @workflow.run
    async def run(self, template_contents, kw={}):
        await asyncio.sleep(10)
        zip_buffer = io.BytesIO()
        try:
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for model in template_contents:
                    byte_content = bytes(model["content"])
                    if isinstance(byte_content, bytes):
                        # Nếu là byte string, giải mã nó
                        content = byte_content.decode("utf-8")
                    else:
                        # Nếu không phải byte string, không thể giải mã
                        workflow.logger.error(f"Invalid content type for {model['filename']}")
                        raise ValueError(f"Content of {model['filename']} is not a valid byte string", type(model["content"]))

                    xml_dict = xmltodict.parse(content)

                    # Định nghĩa các workflow của unit test generator.
            pass

        except Exception as e:
            workflow.logger.error(f"Error in workflow execution: {e}")
            raise
