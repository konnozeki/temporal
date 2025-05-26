import io
import zipfile
import base64
import xmltodict
import asyncio
from temporalio import workflow
from datetime import timedelta
from ..activities.unit_test_generator import generate_unit_tests, collect_table_contexts
import json


def extract_foreign_keys_from_all(xml_dicts):
    foreign_keys = set()
    for xml_dict in xml_dicts:
        try:
            fields = xml_dict.get("root", {}).get("fields", {}).get("field", [])
            if isinstance(fields, dict):
                fields = [fields]  # convert single field to list
            for field in fields:
                fk = field.get("foreign_key")
                if fk:
                    model_name = fk.split(",")[0].strip()
                    if model_name:
                        foreign_keys.add(model_name)
        except Exception as e:
            workflow.logger.error(f"Error extracting foreign key: {e}")
    return list(foreign_keys)


@workflow.defn(sandboxed=False)
class UnitTestGenerationWorkflow:

    @workflow.run
    async def run(self, template_contents, kw={}):
        zip_buffer = io.BytesIO()
        try:
            xml_contexts = []
            parsed_models = []

            # Parse all XML models first
            for model in template_contents:
                byte_content = bytes(model["content"])
                if isinstance(byte_content, bytes):
                    content = byte_content.decode("utf-8")
                else:
                    workflow.logger.error(f"Invalid content type for {model['filename']}")
                    raise ValueError(f"Content of {model['filename']} is not a valid byte string", type(model["content"]))

                xml_dict = xmltodict.parse(content)
                xml_contexts.append(xml_dict)
                parsed_models.append({"filename": model["filename"], "xml_context": xml_dict})

            # Extract all foreign keys at once
            foreign_list = extract_foreign_keys_from_all(xml_contexts)

            # Load DB context once
            db_context = await workflow.execute_activity(collect_table_contexts, foreign_list, start_to_close_timeout=timedelta(seconds=30))

            # Generate test cases per model
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for parsed in parsed_models:
                    unit_test_files = await workflow.execute_activity(generate_unit_tests, args=[parsed["xml_context"], db_context], start_to_close_timeout=timedelta(seconds=60))

                    for filename, content in unit_test_files.items():
                        if isinstance(content, list):
                            content = json.dumps(content, ensure_ascii=False, indent=2)
                        zip_file.writestr(filename, content)

            # Return base64 encoded zip
            zip_buffer.seek(0)
            zip_content = zip_buffer.getvalue()
            zip_b64 = base64.b64encode(zip_content).decode("utf-8")
            workflow.logger.info("Unit test generation workflow completed successfully")
            return {"zip_content": zip_b64}

        except Exception as e:
            workflow.logger.error(f"Error in unit test generation workflow: {e}")
            raise
