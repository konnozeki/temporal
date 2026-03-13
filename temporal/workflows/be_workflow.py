import io
import zipfile
import base64
import xmltodict
from temporalio import workflow
from datetime import timedelta
from ..activities.be_generator import generate_controller, generate_model, generate_route, generate_view
from ..constants import DEFAULT_TASK_QUEUE
from ..workflows.be_deploy_workflow import BeWorkspaceDeployWorkflow


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
    5. Lên lịch một workflow deploy riêng nếu có artifact backend được sinh ra.
    6. Mã hóa zip sang base64 và trả về.

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
      - `kw`: Dict tùy chọn, có thể chứa cờ điều khiển deploy hoặc giá trị
        mặc định như `system_code`.

    - **Trả về**:
      - Dict có:
        - `"zip_content"`: dữ liệu zip đã mã hóa base64.
        - `"deploy_result"`: trạng thái schedule workflow deploy riêng.
        - `"generated_models"`: danh sách model đã được sinh.

    - **Quy trình chi tiết**:
    ```text
    [XML model files] → [parse XML] → [generate code with activity] → [viết zip file]
    → [schedule deploy workflow nếu cần] → [base64] → [return]
    """

    def __init__(self):
        self.init_route_string = ""
        self.init_view_string = ""
        self.init_controller_string = ""
        self.init_model_string = ""
        self.annotation_string = """from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
"""

    @workflow.run
    async def run(self, template_contents, kw={}):
        """
        Sinh toàn bộ backend artifacts và đóng gói thành ZIP.

        Điểm quan trọng của phiên bản hiện tại:
        - workflow này không trực tiếp ghi vào workspace/repo đích,
        - thay vào đó nó chỉ khởi tạo một child workflow deploy riêng với
          `ParentClosePolicy.ABANDON`,
        - vì vậy nếu deploy thất bại, kết quả ZIP vẫn được giữ nguyên để
          tải xuống và import thủ công.
        """
        # Tạo buffer zip
        zip_buffer = io.BytesIO()
        generated_artifacts = []

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
                    model_name: str = xml_dict["root"]["model"].strip()

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
                        class_string = model_name.replace("_", " ").title().replace(" ", "_")
                        self.annotation_string += f"\tfrom .{model_name}_model import {class_string}\n"
                        generated_artifacts.append(
                            {
                                "model_name": model_name,
                                "system_code": xml_dict["root"].get("system_code", kw.get("system_code", "")).strip().upper(),
                                "class_name": class_string,
                                "model": model_string,
                                "controller": controller_string,
                                "route": route_string,
                                "view": view_string,
                            }
                        )
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
                zip_file.writestr(f"model/annotations.py", self.annotation_string)
            # Lấy nội dung zip và trả về kết quả
            zip_buffer.seek(0)
            zip_content = zip_buffer.getvalue()
            zip_b64 = base64.b64encode(zip_content).decode("utf-8")

            deploy_result = {"status": "skipped", "reason": "no generated artifacts"}
            if generated_artifacts:
                try:
                    deploy_workflow_id = f"{workflow.info().workflow_id}-deploy"
                    await workflow.start_child_workflow(
                        BeWorkspaceDeployWorkflow.run,
                        args=[generated_artifacts, kw],
                        id=deploy_workflow_id,
                        task_queue=DEFAULT_TASK_QUEUE,
                        parent_close_policy=workflow.ParentClosePolicy.ABANDON,
                    )
                    deploy_result = {"status": "scheduled", "workflow_id": deploy_workflow_id}
                except Exception as e:
                    deploy_result = {"status": "error", "message": str(e)}
                    workflow.logger.error(f"Error during backend deploy workflow scheduling: {e}")

            # Logging thông tin thành công
            workflow.logger.info("Workflow completed successfully")

            return {
                "zip_content": zip_b64,
                "deploy_result": deploy_result,
                "generated_models": [artifact["model_name"] for artifact in generated_artifacts],
            }

        except Exception as e:
            workflow.logger.error(f"Error in workflow execution: {e}")
            raise
