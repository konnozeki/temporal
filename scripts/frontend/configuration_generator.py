class ConfigurationGenerator:
    """
    Lớp `ConfigurationGenerator` dùng để sinh mã cấu hình (imports và khai báo module) cho Frontend (thường là React + Ant Design).

    ### Mục đích:
    - Tự động tạo phần cấu hình module trong file `configuration.ts` hoặc `modules.ts`, bao gồm:
        + Import `fields` (định nghĩa cấu trúc cột trong bảng).
        + Import `service` (gọi API).
        + Khai báo đối tượng cấu hình theo `model_name`.

    - Hỗ trợ quy chuẩn hóa cấu trúc folder `services` và `columnsettings` cho từng module.

    ---
    ### Thuộc tính:
    - `xml_dict` (`dict`): Dữ liệu mô tả model (thường từ file XML metadata).
    - `import_string` (`str`): Chuỗi mã `import` sinh tự động.
    - `declare_string` (`str`): Chuỗi cấu hình khai báo module theo `model_name`.

    ---
    ### Phương thức:

    #### `__init__(self, xml_dict)`
    - Khởi tạo đối tượng với metadata đầu vào.
    - Thiết lập các chuỗi `import_string` và `declare_string` ban đầu.

    #### `generate(self)`
    - Phân tích dữ liệu từ `xml_dict["root"]` để lấy:
        + `model_name`: Tên model (ví dụ: `"nagaco_something"`).
        + `module_code`: Mã module (nếu có).
    - Từ `model_name`, suy ra:
        + `class_name`: Định dạng PascalCase, dùng cho file/component/class FE.
        + `object_name`: Định dạng camelCase, dùng cho tên biến FE.
    - Trả về tuple `(import_string, declare_string)`, có thể nối vào một file cấu hình tổng.
    ---
    ### Lưu ý:
    - Mục tiêu chính là để hỗ trợ tự động hóa cập nhật file cấu hình, đặc biệt trong hệ thống quản lý nhiều module.
    - Nên dùng kết hợp với các generator backend để giữ đồng bộ model ↔ cấu hình FE.
    """

    def __init__(self, xml_dict):
        self.xml_dict = xml_dict
        self.import_string = ""
        self.declare_string = ""

    def generate(self):
        """
        Phương thức `generate` dùng để sinh mã cấu hình module cho frontend (thường trong dự án React hoặc Vue), bao gồm:
        - Chuỗi `import` để import field config và service tương ứng từ tên model.
        - Khối cấu hình để khai báo trong đối tượng `modules` hoặc `configuration`.

        ---
        ### Mục đích:
        - Tự động sinh đoạn cấu hình frontend dựa trên thông tin metadata (`xml_dict`) từ backend hoặc file XML cấu hình.
        - Giảm lỗi gõ tay khi cấu hình các module mới trong hệ thống nhiều bảng/phân hệ.

        ---
        ### Cách hoạt động:
        1. Lấy thông tin từ `self.xml_dict["root"]`, bao gồm:
            - `model_name`: tên của model ví dụ `"nagaco_product"`.
            - `module_code`: mã phân hệ dùng cho phân quyền hoặc phân tách dữ liệu.
        2. Sinh:
            - `class_name`: PascalCase version của `model_name`, dùng để import các file `Fields` và `Service`.
            - `object_name`: CamelCase version, dùng làm biến service.

        3. Ghép nối `import_string` và `declare_string`:
            ```ts
            import { fields as NagacoProductFields } from "../columnsettings/NagacoProductFields";
            import { nagacoProductService } from "../services/NagacoProductService";

            nagaco_product: {
                service: nagacoProductService,
                moduleCode: 'PRD',
                fields: NagacoProductFields
            },
            ```

        ---
        ### Trả về:
        - Tuple `(import_string, declare_string)`:
            + `import_string`: chuỗi các dòng `import` đầy đủ.
            + `declare_string`: chuỗi khai báo từng module trong đối tượng cấu hình chính.

        ---
        ### Xử lý lỗi:
        - Nếu thiếu `model_name`, sẽ raise `ValueError`.
        - Nếu có lỗi bất kỳ khác (ví dụ sai định dạng), sẽ trả về chuỗi lỗi dưới dạng `(str(e), str(e))`.

        ---
        ### Ví dụ:
        ```python
        xml_dict = {
            "root": {
                "model": "nagaco_order",
                "module_code": "ORD"
            }
        }

        config = ConfigurationGenerator(xml_dict)
        imports, declarations = config.generate()
        print(imports)
        print(declarations)
        ```

        => Output:
        ```ts
        import { fields as NagacoOrderFields } from "../columnsettings/NagacoOrderFields";
        import { nagacoOrderService } from "../services/NagacoOrderService";

        nagaco_order: {
            service: nagacoOrderService,
            moduleCode: 'ORD',
            fields: NagacoOrderFields
        },
        ```

        ---
        ### Ghi chú:
        - Được dùng trong quá trình build file `configuration.js` tổng hợp cho toàn bộ hệ thống frontend.
        - Hữu ích trong hệ thống sinh mã tự động từ metadata (Low-code/No-code hoặc Backend-driven UI).
        """
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
