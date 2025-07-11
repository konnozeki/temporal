import io
import zipfile
import base64
import xmltodict
from temporalio import workflow
from datetime import timedelta
from ..activities.be_generator import *
import asyncio


@workflow.defn(sandboxed=False)
class BeCodeGenerationWorkflow:
    """
    Workflow thực hiện **tự động sinh mã backend** cho các model Odoo dựa trên cấu trúc XML. Mã sinh ra bao gồm:
    - Model (`_model.py`)
    - Controller (`_controller.py`)
    - Route (`_route.py`)
    - View (`_view.py`)
    - Và các file `__init__.py` để import tự động trong thư mục.

    Workflow này chạy trên Temporal và sử dụng các hoạt động (`activity`) được định nghĩa trong `be_generator`.

    Cách hoạt động:
    ---------------
    1. Nhận danh sách các file XML (`template_contents`) — mỗi file mô tả 1 model.
    2. Parse nội dung XML thành `dict`.
    3. Gọi các activity:
       - `generate_model`
       - `generate_controller`
       - `generate_route`
       - `generate_view`
    4. Ghi nội dung sinh ra vào file zip theo cấu trúc thư mục.
    5. Mã hóa zip sang base64 và trả về.

    Thuộc tính lớp:
    ---------------
    - `self.init_route_string`: nội dung file `route/__init__.py`
    - `self.init_view_string`: nội dung file `model/view/__init__.py`
    - `self.init_controller_string`: nội dung file `controller/__init__.py`
    - `self.init_model_string`: nội dung file `model/__init__.py`

    Method:
    -------
    ### `async def run(self, template_contents, kw={})`
    - **Tham số**:
      - `template_contents`: List[Dict], chứa `filename` và `content` (dạng bytes hoặc chuỗi encode).
      - `kw`: Dict tùy chọn (không sử dụng trong hiện tại).

    - **Trả về**:
      - Dict có key `"zip_content"` chứa dữ liệu zip đã mã hóa base64.

    - **Quy trình chi tiết**:
    ```text
    [XML model files] → [parse XML] → [generate code with activity] → [viết zip file] → [base64] → [return]
    """

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
            # await workflow.sleep(5)
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
