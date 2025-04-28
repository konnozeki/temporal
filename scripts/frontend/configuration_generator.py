class ConfigurationGenerator:
    def __init__(self, xml_dict):
        self.xml_dict = xml_dict
        self.import_string = ""
        self.declare_string = ""

    def generate(self):
        try:
            root = self.xml_dict.get("root", {})
            model_name = root.get("model", "").strip()
            module_code = root.get("module_code", "") or ""

            if not model_name:
                raise ValueError("Model name is missing")

            class_name = model_name.replace("_", " ").title().replace(" ", "")
            object_name = class_name[0].lower() + class_name[1:]

            self.import_string += f'import {{ fields as {class_name}Fields }} from "../columnsettings/{class_name}Fields";\n' f'import {{ {object_name}Service }} from "../services/{class_name}Service";\n'

            self.declare_string += f"    {model_name}: {{\n" f"        service: {object_name}Service,\n" f"        moduleCode: '{module_code}',\n" f"        fields: {class_name}Fields\n" f"    }},\n"
            return self.import_string, self.declare_string

        except Exception as e:
            return str(e), str(e)
