from temporalio import activity


class FieldsGenerator:
    """
    Lớp `FieldsGenerator` dùng để sinh mã cấu hình `fields` cho frontend (thường dạng JavaScript) từ metadata XML.

    ### Mục đích:
    - Tự động chuyển đổi metadata (từ XML) thành cấu hình cột dùng trong form/table.
    - Hỗ trợ các thuộc tính như: label, alias, reference, type, required, hidden, span, v.v.
    """

    def __init__(self, xml_dict):
        self.xml_dict = xml_dict

    def generate(self):
        """
        Sinh mã JavaScript định nghĩa `fields` từ thông tin các trường trong XML.

        ### Cách hoạt động:
        - Duyệt qua từng `field` trong `xml_dict["root"]["fields"]["field"]`.
        - Chuyển đổi các thuộc tính như:
            + `name`, `label`, `type`, `show_type`, `not_null`, `alias`, `span`, `foreign_key`, ...
        - Xử lý logic hiển thị (`default_display`) và ánh xạ `foreign_key.name/code`.
        - Thêm mặc định trường `write_date` vào cuối.

        ### Trả về:
        - Chuỗi JavaScript: định nghĩa `const fields = [...]` dùng cho frontend (đặc biệt là `columnSettings`).

        ### Ghi chú:
        - Được dùng để tự động sinh file `SomeModelFields.ts`.
        - Nếu có lỗi xảy ra, sẽ log lỗi và raise lại để workflow phía Temporal xử lý.
        """
        try:
            fields = self.xml_dict["root"]["fields"]["field"]
            xml_fields = fields if isinstance(fields, list) else [fields]

            def get_value(field, key, default=""):
                val = field.get(key)
                if val is None:
                    return default
                return val.strip().lower()

            field_list = []
            for field in xml_fields:
                if field is None:
                    continue

                field_type = get_value(field, "type", "string")
                field_show_type = get_value(field, "show_type", "textbox")
                field_label = get_value(field, "label")
                field_name = get_value(field, "name")
                field_data_index = field_name
                field_alias = get_value(field, "alias")
                field_require = get_value(field, "not_null", "false") in ("1", "true")
                field_span = get_value(field, "span", "24")
                field_auto_generate = get_value(field, "auto_generate", "false") in ("1", "true")
                field_reference = get_value(field, "reference")
                if field_reference == "khóa chính":
                    field_reference = ""
                field_unique = get_value(field, "unique", "false") in ("1", "true", "c")
                field_default_display = get_value(field, "default_display", "c")
                field_foreign_key = get_value(field, "foreign_key")

                hidden = field_name == "id"
                init = default = False
                match field_default_display:
                    case "d":
                        default = True
                    case "c":
                        init = True
                    case "h":
                        hidden = True

                if field_foreign_key:
                    temp_arr = field_foreign_key.split(",")
                    if "name" in temp_arr:
                        field_alias += "na"
                        field_data_index += ".name"
                    elif "code" in temp_arr:
                        field_alias += "co"
                        field_data_index += ".code"

                field_list.append(
                    f"""{{
                    code: '{field_name}',
                    alias: '{field_alias}',
                    label: '{field_label}',
                    reference: '{field_reference}',
                    dataIndex: '{field_data_index}',
                    dataType: '{field_type}',
                    type: '{field_show_type}',
                    hidden: {str(hidden).lower()},
                    init: {str(init).lower()},
                    default: {str(default).lower()},
                    required: {str(field_require).lower()},
                    unique: {str(field_unique).lower()},
                    auto_generate: {str(field_auto_generate).lower()},
                    span: {field_span},
                }},"""
                )

            # Append write_date field
            field_list.append(
                """{
                code:'write_date',
                alias: 'wd',
                label: "Thời gian cập nhật cuối cùng",
                default: false,
                hidden: false,
                init: false,
                dataType: "datetime",
                type:'textbox',
                dataIndex: 'write_date',
                auto_generate: true,
                required: false,
            },"""
            )

            fields_str = "\n".join(field_list)
            result = f"const fields = [\n{fields_str}\n];\nexport {{ fields }};"
            return result

        except Exception as e:
            activity.logger.error(f"Error in generate_column_setting: {e}")
            raise
