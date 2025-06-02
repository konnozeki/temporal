class NavigationGenerator:
    def __init__(self, xml_dict, module_name="categories"):
        self.xml_dict = xml_dict
        self.module_name = module_name

    def generate(self):
        try:
            root = self.xml_dict.get("root", {})
            model_name = root.get("model", "").strip()
            sub_system_code = root.get("sub_system_code", "") or ""
            module_code = root.get("module_code", "") or ""

            if not model_name:
                raise ValueError("Model name is missing")

            navigation_string = (
                f"{{\n"
                f"    key: '{self.module_name}-{model_name}',\n"
                f"    code: `${{SYSTEM_CODE}}_{sub_system_code}-{module_code}-R`,\n"
                f"    path: `${{APP_PREFIX_PATH}}/{self.module_name}/{model_name}`,\n"
                f"    title: 'sidenav.{self.module_name}.{model_name}',\n"
                f"    breadcrumb: false,\n"
                f"    submenu: [],\n"
                f"}}"
            )

            return navigation_string

        except Exception as e:
            return str(e)
