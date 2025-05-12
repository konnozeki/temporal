import io
import zipfile
import base64
import xmltodict
from temporalio import workflow
from datetime import timedelta
from ..activities.be_generator import *


@workflow.defn(sandboxed=False)
class BeCodeGenerationWorkflow:
    def __init__(self):
        self.init_route_string = ""
        self.init_view_string = ""
        self.init_controller_string = ""
        self.init_model_string = ""

    @workflow.run
    async def run(self, template_contents, kw={}):
        # Tạo buffer zip
        zip_buffer = io.BytesIO()

        try:
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                # Lặp qua từng model trong template_contents
                for model in template_contents:
                    byte_content = bytes(model["content"])
                    # Kiểm tra xem content có phải là byte string không
                    if isinstance(byte_content, bytes):
                        # Nếu là byte string, giải mã nó
                        content = byte_content.decode("utf-8")
                    else:
                        # Nếu không phải byte string, không thể giải mã
                        workflow.logger.error(f"Invalid content type for {model['filename']}")
                        raise ValueError(f"Content of {model['filename']} is not a valid byte string", type(model["content"]))

                    xml_dict = xmltodict.parse(content)
                    model_name = xml_dict["root"]["model"].strip()

                    # Logging thông tin để theo dõi
                    workflow.logger.info(f"Processing model: {model_name}")

                    # Gọi các hoạt động trong workflow với timeout
                    try:
                        model_string = await workflow.execute_activity(generate_model, xml_dict, start_to_close_timeout=timedelta(seconds=30))
                        controller_string = await workflow.execute_activity(generate_controller, xml_dict, start_to_close_timeout=timedelta(seconds=30))
                        route_string = await workflow.execute_activity(generate_route, xml_dict, start_to_close_timeout=timedelta(seconds=30))
                        view_string = await workflow.execute_activity(generate_view, xml_dict, start_to_close_timeout=timedelta(seconds=30))
                        self.init_route_string += f"from . import {model_name}_route\n"
                        self.init_view_string += f"from . import {model_name}_view\n"
                        self.init_controller_string += f"from . import {model_name}_controller\n"
                        self.init_model_string += f"from . import {model_name}_model\n"
                    except Exception as e:
                        workflow.logger.error(f"Error during activity execution: {e}")
                        raise

                    # Tạo tên file cho các tệp cần nén
                    zip_file.writestr(f"controller/{model_name}_controller.py", controller_string)
                    zip_file.writestr(f"route/{model_name}_route.py", route_string)
                    zip_file.writestr(f"model/{model_name}_model.py", model_string)
                    zip_file.writestr(f"model/view/{model_name}_view.py", view_string)

                zip_file.writestr(f"controller/__init__.py", self.init_controller_string)
                zip_file.writestr(f"route/__init__.py", self.init_route_string)
                zip_file.writestr(f"model/__init__.py", self.init_model_string)
                zip_file.writestr(f"model/view/__init__.py", self.init_view_string)
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
