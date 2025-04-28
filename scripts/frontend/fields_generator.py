class FieldsGenerator:
    def __init__(self, xml_dict):
        self.xml_dict = xml_dict

    def generate(self):
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
            return str(e)
