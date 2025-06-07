class NavigationGenerator:
    """
    Lớp `NavigationGenerator` dùng để sinh ra đoạn cấu hình điều hướng (navigation item) trong frontend,
    dựa trên metadata XML định nghĩa model backend.

    ### Mục đích:
    - Tự động tạo phần tử điều hướng (navigation item) cho sidebar/menu từ file cấu hình XML.
    - Chuẩn hóa định dạng theo thiết kế frontend (thường dùng trong hệ thống Ant Design, React Router, v.v).

    ### Thuộc tính:
    - `xml_dict` (dict): Metadata cấu hình của model được parse từ XML.
    - `module_name` (str): Tên nhóm module (ví dụ: `"categories"`, `"management"`, ...), mặc định là `"categories"`.
    """

    def __init__(self, xml_dict, module_name="categories"):
        self.xml_dict = xml_dict
        self.module_name = module_name

    def generate(self):
        """
        Sinh ra chuỗi JavaScript object định nghĩa một navigation item.

        ### Cách hoạt động:
        - Lấy các giá trị từ `root` trong `xml_dict` gồm:
            + `model_name`: Tên bảng chính.
            + `sub_system_code`, `module_code`: Mã phụ hệ thống và module tương ứng.
        - Chèn vào chuỗi định dạng gồm:
            + `key`: Khóa điều hướng duy nhất (dạng `moduleName-modelName`).
            + `code`: Mã phân quyền động theo format: `${SYSTEM_CODE}_<sub>-<mod>-R`.
            + `path`: URL đầy đủ để truy cập.
            + `title`: Dùng cho `i18n` (ví dụ: `'sidenav.categories.supply'`).
            + `breadcrumb`, `submenu`: Cấu hình hiển thị thêm.

        ### Trả về:
        - `navigation_string` (str): Chuỗi object JavaScript có thể dùng trong file `navigation.config.js`.

        ### Ghi chú:
        - Nếu thiếu `model_name`, sẽ raise lỗi rõ ràng.
        - Chuỗi kết quả có thể trực tiếp copy dán vào cấu hình navigation của frontend.

        """
        try:
            root = self.xml_dict.get("root", {})
            model_name = root.get("model", "").strip()
            sub_system_code = root.get("sub_system_code", "") or ""
            module_code = root.get("module_code", "") or ""

            if not model_name:
                raise ValueError("Model name is missing")

            navigation_string = f"{{\n" f"    key: '{self.module_name}-{model_name}',\n" f"    code: `${{SYSTEM_CODE}}_{sub_system_code}-{module_code}-R`,\n" f"    path: `${{APP_PREFIX_PATH}}/{self.module_name}/{model_name}`,\n" f"    title: 'sidenav.{self.module_name}.{model_name}',\n" f"    breadcrumb: false,\n" f"    submenu: [],\n" f"}}"

            return navigation_string

        except Exception as e:
            return str(e)
