class ServiceGenerator:
    def __init__(self):
        pass

    def generate(self, model_name, xml_dict):
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
        body_lines = [
            f"        if (request.{field['name']} !== null && request.{field['name']} !== undefined) bodyFormData.append('{field['name']}', "
            + ("(request.{field['name']} === true ? 1 : 0)" if field["type"].strip() == "bool" else f"request.{field['name']}")
            + ");"
            for field in fields
            if field and field["name"].strip() not in auto_generate_fields and field["name"].strip() != "id"
        ]
        return f"""
    prepareFormData = (request = {{}}) => {{
        var bodyFormData = new FormData();
{chr(10).join(body_lines)}
        return bodyFormData;
    }};
"""
