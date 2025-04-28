from temporalio import workflow
from ..activities.fe_generator import generate_column_setting, generate_i18n, generate_menu, generate_service, generate_configuration
import xmltodict
import io
import zipfile


@workflow.defn
class FeCodeGenerationWorkflow:
    def __init__(self):
        self.configuration_import_string = ""
        self.configuration_declare_string = "export const config = {"
        self.navigation_string = ""

    @workflow.run
    async def run(self, template_contents):
        # Tạo buffer zip
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Lặp qua từng model trong template_contents
            for model in template_contents:
                xml_dict = xmltodict.parse(model["content"].decode("utf-8"))
                model_name = xml_dict["root"]["model"].strip()
                class_name = model_name.replace("_", " ").title().replace(" ", "")

                # Gọi các hoạt động trong workflow
                column_setting_string = await generate_column_setting(xml_dict)
                service_string = await generate_service(model["filename"], xml_dict)
                translation_string_vi, translation_string_en = await generate_i18n(xml_dict)

                # Tạo tên file cho các tệp cần nén
                column_setting_file_name = f"columnsettings/{class_name}Fields.js"
                service_string_file_name = f"services/{class_name}Service.js"
                translation_vi_file_name = f"translations/{model_name}/vi.json"
                translation_en_file_name = f"translations/{model_name}/en.json"

                # Viết các tệp vào trong zip
                zip_file.writestr(column_setting_file_name, column_setting_string)
                zip_file.writestr(service_string_file_name, service_string)
                zip_file.writestr(translation_vi_file_name, translation_string_vi)
                zip_file.writestr(translation_en_file_name, translation_string_en)

                # Xử lý navigation và configuration
                menu_string = generate_menu(xml_dict)
                import_string, declare_string = generate_configuration(xml_dict)
                self.navigation_string += menu_string
                self.configuration_import_string += import_string
                self.configuration_declare_string += declare_string

            # Tạo file configuration.js
            zip_file.writestr(
                f"configuration/config.js",
                self.configuration_import_string + self.configuration_declare_string + "}",
            )
            zip_file.writestr("navigation/navigation.js", self.navigation_string)

        # Lấy nội dung zip và trả về kết quả
        zip_buffer.seek(0)
        zip_content = zip_buffer.getvalue()

        return {
            "zip_content": zip_content,
            "headers": [
                ("Content-Type", "application/zip"),
                ("Content-Disposition", 'attachment; filename="output_frontend.zip"'),
            ],
        }
