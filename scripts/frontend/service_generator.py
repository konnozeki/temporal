class ServiceGenerator:
    """
    Lớp `ServiceGenerator` sinh ra class service frontend (JavaScript) cho từng model,
    kế thừa từ một service gốc theo hệ thống, phục vụ cho việc gọi API và xử lý dữ liệu form.

    ### Mục đích:
    - Tự động hóa việc tạo các phương thức gọi API `getBy<ForeignKey>`, `getCountBy<ForeignKey>`.
    - Sinh hàm `prepareFormData` chuẩn hóa dữ liệu trước khi gửi lên server.
    - Đảm bảo đồng bộ cấu trúc frontend theo metadata được khai báo trong XML.

    ### Thuộc tính:
    - Không có thuộc tính khởi tạo cố định ngoài `prefix` (được gán từ `system_code`).
    """

    def __init__(self):
        pass

    def generate(self, model_name, xml_dict):
        """
        Sinh mã nguồn định nghĩa một class service cụ thể cho model.

        ### Đầu vào:
        - `model_name` (str): Tên bảng/model, ví dụ: `"fin_su_increment"`.
        - `xml_dict` (dict): Metadata cấu hình được parse từ XML.

        ### Hoạt động:
        - Tạo tên class chuẩn (`FinSuIncrementService`) và object export (`finSuIncrementService`).
        - Sinh các hàm phụ trợ để:
            + Gọi API theo foreign key.
            + Gửi form data đã chuẩn hóa (hàm `prepareFormData`).
        - Lọc các trường `auto_generate` để loại khỏi phần form gửi.

        ### Trả về:
        - Chuỗi JS class service hoàn chỉnh, sẵn để lưu vào `services/<ClassName>Service.js`.
        """
        try:
            class_name = model_name.replace("_", " ").title().replace(" ", "")
            object_name = class_name[0].lower() + class_name[1:]
            fields = xml_dict.get("root", {}).get("fields", {}).get("field", [])
            self.prefix = xml_dict.get("root", {}).get("system_code", "SYS")
            service_prefix = self.prefix.title()
            if not isinstance(fields, list):
                fields = [fields]

            foreign_keys = list(set([field["name"].replace("_id", "") for field in fields if "foreign_key" in field and field["foreign_key"] for fk in field["foreign_key"].strip().split(",")]))
            auto_generate_fields = [field["name"] for field in fields if field.get("auto_generate") == "1"]

            return f"""import {service_prefix}Service from "./{service_prefix}Service";

const MODEL = '{model_name}';

class {class_name}Service extends {service_prefix}Service {{
    constructor() {{
        super(MODEL);
    }}
{self._generate_foreign_key_methods(foreign_keys)}
{self._generate_prepare_form_data(fields, auto_generate_fields)}
}}

export const {object_name}Service = new {class_name}Service();
"""
        except Exception as e:
            return str(e)

    def _generate_foreign_key_methods(self, foreign_keys):
        """
        Sinh hàm `getBy<ForeignKey>` và `getCountBy<ForeignKey>` cho từng trường liên kết.

        ### Đầu vào:
        - `foreign_keys` (List[str]): Danh sách các trường khóa ngoại (đã loại `_id`).

        ### Đầu ra:
        - Chuỗi các hàm dùng để gọi API theo foreign key (được nhúng vào trong class).
        """
        return "\n".join(
            f"""
    getBy{fk.title().replace("_", "")} = (request = {{}}) => {{
        return this.getByForeignKey('{fk}', request);
    }}

    getCountBy{fk.title().replace("_", "")} = (request = {{}}) => {{
        return this.getCountByForeignKey('{fk}', request);
    }}
"""
            for fk in foreign_keys
        )

    def _generate_prepare_form_data(self, fields, auto_generate_fields):
        """
        Sinh hàm `prepareFormData` để chuẩn hóa dữ liệu trước khi gửi lên API.

        ### Đầu vào:
        - `fields` (List[dict]): Danh sách field từ XML.
        - `auto_generate_fields` (List[str]): Các trường không nên gửi (vì được backend sinh tự động).

        ### Logic xử lý:
        - Bỏ qua các trường auto-generate và trường `id`.
        - Nếu field có kiểu `bool`, chuyển `true/false` sang `1/0`.
        - Gọi `bodyFormData.append` cho mỗi trường có dữ liệu.

        ### Trả về:
        - Chuỗi code định nghĩa hàm `prepareFormData` cho class.
        """
        body_lines = []

        for field in fields:
            name = field.get("name", "").strip()
            field_type = field.get("type", "").strip()

            if not field or name in auto_generate_fields or name == "id":
                continue

            if field_type == "bool":
                line = f"        if (request.{name} !== null && request.{name} !== undefined) " f"bodyFormData.append('{name}', (request.{name} === true ? 1 : 0));"
            elif field_type in ["file", "image"]:
                line = f"        if (request.{name} !== null && request.{name} !== undefined) " f"bodyFormData.append('{name}', request.{name});\n        if (request.f{name} !== null && request.f{name} !== undefined) " f"bodyFormData.append('f{name}', request.f{name});"
            else:
                line = f"        if (request.{name} !== null && request.{name} !== undefined) " f"bodyFormData.append('{name}', request.{name});"

            body_lines.append(line)
        return f"""
    prepareFormData = (request = {{}}) => {{
        var bodyFormData = new FormData();
{chr(10).join(body_lines)}
        return bodyFormData;
    }};
"""
