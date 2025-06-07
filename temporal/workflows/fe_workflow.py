import io
import zipfile
import base64
import xmltodict
from temporalio import workflow
from datetime import timedelta
from ..activities.fe_generator import generate_column_setting, generate_i18n, generate_menu, generate_service, generate_configuration
import asyncio


@workflow.defn(sandboxed=False)
class FeCodeGenerationWorkflow:
    """
    Workflow dùng Temporal để **sinh mã frontend** từ tập tin XML mô tả model. Các phần sinh ra bao gồm:
    - `columnsettings`: cấu hình hiển thị bảng
    - `services`: service class thao tác API
    - `translations`: bản dịch đa ngôn ngữ (vi/en)
    - `configuration`: import và cấu hình toàn cục
    - `navigation`: cấu trúc menu điều hướng

    Cách hoạt động:
    ---------------
    1. Nhận danh sách các file XML (`template_contents`), mỗi file chứa nội dung mô tả 1 model.
    2. Parse XML → Dict (`xml_dict`)
    3. Gọi các activity với timeout:
       - `generate_column_setting`
       - `generate_service`
       - `generate_i18n`
       - `generate_menu`
       - `generate_configuration`
    4. Ghi các file đã sinh vào một file ZIP (dạng base64) để trả về client.

    Thuộc tính lớp:
    ---------------
    - `self.configuration_import_string`: phần import trong `config.js`
    - `self.configuration_declare_string`: phần khai báo model trong `config.js`
    - `self.navigation_string`: nội dung file `navigation.js`
    - `self.system_code`, `self.sub_system_code`: mã hệ thống và phân hệ, gắn vào config.

    Phương thức:
    ------------
    ### `async def run(self, template_contents, kw={})`
    - **Tham số**:
      - `template_contents`: List[Dict], mỗi phần tử gồm `filename` và `content` (dạng bytes).
      - `kw`: Dict tùy chọn (không sử dụng trong phiên bản hiện tại).

    - **Trả về**:
      - Dict chứa `"zip_content"` (dữ liệu zip đã encode base64).

    - **Chi tiết xử lý**:
    ```text
    [XML] → [parse] → [generate từng phần] → [ghi file zip] → [base64] → [trả kết quả]
    """

    def __init__(self, **kw):
        self.configuration_import_string = ""
        self.system_code = kw.get("system_code", "SYS")
        self.sub_system_code = kw.get("sub_system_code", "SUB")
        self.configuration_declare_string = f"""export const config = {{
        SYSTEM_CODE: "{self.system_code}",
        SUB_SYSTEM_CODE: "{self.sub_system_code}",
        """
        self.navigation_string = ""

    @workflow.run
    async def run(self, template_contents, kw={}):
        # await workflow.sleep(5)
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
                    class_name = model_name.replace("_", " ").title().replace(" ", "")

                    # Logging thông tin để theo dõi
                    workflow.logger.info(f"Processing model: {model_name}")

                    # Gọi các hoạt động trong workflow với timeout
                    try:
                        column_setting_string = await workflow.execute_activity(generate_column_setting, xml_dict, start_to_close_timeout=timedelta(seconds=30))
                        service_string = await workflow.execute_activity(generate_service, args=[model_name, xml_dict], start_to_close_timeout=timedelta(seconds=30))
                        translation_string_vi, translation_string_en = await workflow.execute_activity(generate_i18n, xml_dict, start_to_close_timeout=timedelta(seconds=30))
                        # service_string, translation_string_vi, translation_string_en = "", "", ""
                    except Exception as e:
                        workflow.logger.error(f"Error during activity execution: {e}")
                        raise

                    # Tạo tên file cho các tệp cần nén
                    class_file_prefix = f"{class_name}"
                    zip_file.writestr(f"columnsettings/{class_file_prefix}Fields.js", column_setting_string)
                    zip_file.writestr(f"services/{class_file_prefix}Service.js", service_string)
                    zip_file.writestr(f"translations/{model_name}/vi.json", translation_string_vi)
                    zip_file.writestr(f"translations/{model_name}/en.json", translation_string_en)

                    # Xử lý navigation và configuration
                    try:
                        menu_string = await workflow.execute_activity(generate_menu, xml_dict, start_to_close_timeout=timedelta(seconds=30))
                        import_string, declare_string = await workflow.execute_activity(generate_configuration, xml_dict, start_to_close_timeout=timedelta(seconds=30))
                        self.navigation_string += menu_string
                        self.configuration_import_string += import_string
                        self.configuration_declare_string += declare_string
                    except Exception as e:
                        workflow.logger.error(f"Error during configuration generation: {e}")
                        raise

                # Tạo file configuration.js
                zip_file.writestr(
                    "configuration/config.js",
                    self.configuration_import_string + self.configuration_declare_string + "}",
                )
                zip_file.writestr("navigation/navigation.js", self.navigation_string)

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
