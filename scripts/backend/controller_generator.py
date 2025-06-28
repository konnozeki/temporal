from enum import Enum


class TypeAlias(Enum):
    varchar = "Char"
    text = "Text"
    binary = "Binary"
    bool = "Boolean"
    date = "Date"
    datetime = "Datetime"
    float = "Float"
    double = "Float"
    many2one = "Many2one"
    integer = "Integer"
    int = "Integer"
    file = "Char"
    image = "Char"
    smallint = "Integer"


class Field:
    """
    Lớp `Field` đại diện cho một trường dữ liệu (field) được cấu hình động từ metadata,
    dùng để sinh ra các cấu hình kiểm tra (rules), thông báo lỗi (messages), định nghĩa model Odoo,
    và các thông tin liên quan đến field như kiểu dữ liệu, liên kết khóa ngoại, kiểu số, kiểu file...

    ### Mục đích:
    - Tự động hóa việc tạo cấu hình validate, message, và mã định nghĩa model trong các hệ thống backend (như Odoo).
    - Chuẩn hóa đầu vào từ bảng cấu hình để giảm lỗi và tăng hiệu quả sinh mã.

    ### Thuộc tính:
    - `self.data` (dict): Dữ liệu mô tả field (thường từ cấu hình bảng hoặc file).
    - `self.validated_attributes` (List[str]): Danh sách các thuộc tính có thể áp dụng validate.
    - `self.field_list` (List[str]): Danh sách tên field dùng để render (sử dụng ngoài class này).
    - `self.number_field_list` (List[str]): Danh sách field có kiểu số (sử dụng ngoài class này).

    ### Các phương thức chính:
    - `get_name()`: Lấy tên chuẩn hóa của trường.
    - `is_number()`: Kiểm tra xem trường có phải kiểu số không.
    - `is_file()`: Kiểm tra xem trường có phải kiểu file không.
    - `generate_rules()`: Sinh rule validation từ cấu hình field.
    - `generate_messages()`: Sinh thông báo lỗi cho từng rule.
    - `generate_linked_table()`: Trả về tên trường nếu có liên kết foreign key.

    ### Ghi chú:
    - Class này thường được sử dụng trong vòng lặp duyệt nhiều field để sinh ra cấu hình toàn cục cho một model hoặc form.
    - Các phương thức trả về chuỗi định dạng giống JSON hoặc Python dict, phù hợp để nhúng vào file cấu hình hoặc ghi ra file mã nguồn.

    ### Ví dụ sử dụng:
    ```python
    f = Field({
        "name": "email",
        "type": "char",
        "not_null": "1",
        "email": "1"
    })
    print(f.generate_rules())   # => Sinh rule kiểm tra định dạng email
    print(f.generate_messages())  # => Sinh message tương ứng
    ```
    """

    def __init__(self, field_data):
        self.data = field_data
        self.validated_attributes = ["not_null", "min_length", "max_length", "range_length", "min", "max", "range", "step", "email", "url", "date", "number", "digits", "equalTo", "file.type", "file.size", "unique", "foreign_key", "regexp"]
        self.field_list = []
        self.number_field_list = []

    def get_name(self):
        """
        Trích xuất và chuẩn hóa trường `name` từ thuộc tính `self.data`.

        - Thực hiện:
            + Kiểm tra xem khóa `"name"` có tồn tại và không rỗng trong `self.data`.
            + Nếu có, trả về chuỗi `name` sau khi loại bỏ khoảng trắng đầu/cuối và chuyển thành chữ thường.
            + Nếu không có hoặc giá trị là None, trả về chuỗi rỗng.

        - Trả về:
            + Chuỗi `name` đã chuẩn hóa hoặc chuỗi rỗng nếu không hợp lệ.
        """
        if "name" in self.data and self.data["name"] is not None:
            return self.data["name"].strip().lower()
        else:
            return ""

    def is_number(self):
        """
        Kiểm tra xem trường `type` trong `self.data` có phải là kiểu số hay không.

        - Thực hiện:
            + Lấy giá trị của khóa `"type"` trong `self.data` nếu tồn tại và không phải None.
            + Chuẩn hóa giá trị về dạng chữ thường, loại bỏ khoảng trắng.
            + Kiểm tra xem giá trị đó có nằm trong các kiểu số được chấp nhận: `"int"`, `"smallint"`, `"float"`, `"double"`.

        - Trả về:
            + `True` nếu `type` là một trong các kiểu số trên.
            + `False` nếu không phải hoặc không có giá trị hợp lệ.
        """
        if "type" in self.data and self.data["type"] is not None:
            type = self.data["type"].strip().lower()
        else:
            type = ""
        return type in ["int", "smallint", "float", "double"]

    def is_file(self):
        """
        Kiểm tra xem trường `type` trong `self.data` có biểu thị một kiểu dữ liệu file hay không.

        - Thực hiện:
            + Lấy giá trị của khóa `"type"` trong `self.data` nếu tồn tại và không phải None.
            + Chuẩn hóa giá trị bằng cách loại bỏ khoảng trắng và chuyển thành chữ thường.
            + Kiểm tra xem giá trị có nằm trong danh sách các kiểu file được chấp nhận: `"file"` hoặc `"image"`.

        - Trả về:
            + `True` nếu `type` là `"file"` hoặc `"image"`.
            + `False` nếu không phải hoặc không có giá trị hợp lệ.
        """
        if "type" in self.data and self.data["type"] is not None:
            type = self.data["type"].strip().lower()
        else:
            type = ""
        return type in ["file", "image"]

    def generate_rules(self, module_name=None) -> str:
        """
        Sinh ra chuỗi rule định dạng theo chuẩn cấu hình kiểm tra (validation rules) cho một field.

        - Tham số:
            + `module_name` (str, optional): Tên module dùng để định danh duy nhất (đặc biệt cho rule `unique`). Mặc định là None.

        - Thực hiện:
            + Lấy tên trường từ `self.data["name"]`, nếu không có thì trả về chuỗi rỗng.
            + Duyệt qua từng thuộc tính hợp lệ trong `self.validated_attributes` để kiểm tra và xử lý:
                * Với các giá trị logic (true/false) → xử lý chuẩn hóa giá trị.
                * Với các rule đặc biệt như `regexp`, `not_null`, `unique`, `foreign_key` → định dạng rule phù hợp.
                * Với các rule liên quan file (`file.size`, `file.type`) → chỉ thêm nếu trường là kiểu file (`is_file()`).
            + Tạo block rule chính với tên field và các rule tương ứng.
            + Nếu có rule file riêng, sinh thêm block phụ với key `'f<name>'`.

        - Trả về:
            + Chuỗi định dạng rule (dạng JSON-like string) có thể nhúng vào file cấu hình validate.
            + Nếu không có rule hợp lệ nào, trả về chuỗi rỗng.

        - Ví dụ đầu ra:
            ```python
            'username': {
                'required': True,
                'min_length': 6,
                'max_length': 32,
                'regexp': r'^[a-z0-9_]+$'
            }
            ```

            Nếu là kiểu file:
            ```python
            'avatar': {
                'required': True
            },
            'favatar': {
                'file.size': '5MB',
                'file.type': 'image/png'
            }
            ```
        """
        name = self.data.get("name", "").strip().lower()
        if not name:
            return ""

        rules = []
        file_rules = []

        type = self.data.get("type")
        type_value = type.strip()
        if type_value == "date":
            rules.append(f"\t\t\t\t\t'{type_value}': True")
        if type_value == "datetime":
            rules.append(f"\t\t\t\t\t'{type_value}': True")

        for attr in self.validated_attributes:
            raw_value = self.data.get(attr)
            if not raw_value or not raw_value.strip():
                continue

            value = raw_value.strip()
            is_true = value == "1" or value.lower() == "true" or value.lower() == "t" or value.lower() == "c" or value.lower() == "đ"

            if attr in {"min", "max", "min_length", "max_length", "step"}:
                rules.append(f"\t\t\t\t\t'{attr}': {int(float(value))}")
            elif attr == "regexp":
                rules.append(f"\t\t\t\t\t'{attr}': r'{value}'")
            elif attr == "not_null" and is_true:
                rules.append("\t\t\t\t\t'required': True")
            elif attr == "unique" and is_true:
                rules.append(f"\t\t\t\t\t'{attr}': '{module_name}.{name}'")
            elif attr in {"email", "url", "date", "number", "digits"} and is_true:
                rules.append(f"\t\t\t\t\t'{attr}': True")
            elif attr == "equalTo":
                rules.append(f"\t\t\t\t\t'{attr}': '{value}'")
            elif attr == "foreign_key":
                cleaned_fk = value.replace(" ", "").replace(",", ".")
                rules.append(f"\t\t\t\t\t'{attr}': '{cleaned_fk}'")
            elif attr in {"file.size", "file.type"} and self.is_file():
                file_rules.append(f"\t\t\t\t\t'{attr}': '{value}'")
            else:
                rules.append(f"\t\t\t\t\t'{attr}': {value}")

        if not rules:
            return ""

        rule_block = f"\t\t\t\t'{name}': {{\n" + ",\n".join(rules) + "\n\t\t\t\t}"
        if file_rules:
            file_block = f"\n\t\t\t\t'f{name}': {{\n" + ",\n".join(file_rules) + "\n\t\t\t\t}"
            return rule_block + "," + file_block
        return rule_block

    def generate_messages(self):
        """
        Sinh ra chuỗi các thông báo lỗi (messages) cho từng rule validation dựa trên `self.data` và `self.validated_attributes`.

        - Thực hiện:
            + Xác định tên trường (`name`) để làm key chính.
            + Duyệt qua từng thuộc tính trong `self.validated_attributes` để kiểm tra có giá trị hay không.
            + Với mỗi thuộc tính hợp lệ:
                * Nếu là các rule boolean (`not_null`, `unique`, `email`, ...) → kiểm tra giá trị có phải `true` hoặc `"1"`.
                * Nếu là rule liên quan đến file (`file.size`, `file.type`) → chỉ thêm nếu là trường file (`self.is_file()`).
                * Với các rule còn lại có thông báo mẫu → thêm trực tiếp.
            + Sinh chuỗi thông báo theo cấu trúc giống định dạng JSON, sử dụng `name` làm key chính.
            + Nếu có rule liên quan đến file, sinh thêm khối `f<name>`.

        - Trả về:
            + Chuỗi biểu diễn các message cho field và các message phụ cho file nếu có.
            + Trả về chuỗi rỗng nếu không có rule hợp lệ.

        - Ví dụ:
            ```python
            'username': {
                "not_null" : "Trường này bắt buộc phải có",
                "min_length" : "Trường này có độ dài nhỏ hơn độ dài cho phép là {1}"
            },
            'fusername': {
                "file.size" : "Kích thước của file lớn hơn {1}"
            }
            ```

        - Ghi chú:
            + Các thông điệp hỗ trợ placeholder `{1}`, `{2}` để  thay thế runtime nếu cần.
            + Hàm này phục vụ cho việc sinh cấu hình validate và messages tự động từ metadata field.
        """
        messages = {
            "not_null": "Trường này bắt buộc phải có",
            "min_length": "Trường này có độ dài nhỏ hơn độ dài cho phép là {1}",
            "max_length": "Trường này có độ dài lớn hơn độ dài cho phép là {1}",
            "range_length": "Trường này có độ dài không nằm trong khoảng cho phép là từ {1} đến {2}",
            "min": "Trường này có giá trị nhỏ hơn giá trị cho phép là {1}",
            "max": "Trường này có giá trị lớn hơn giá trị cho phép là {1}",
            "range": "Trường này có giá trị không nằm trong khoảng cho phép là từ {1} đến {2}",
            "step": "Trường này bước giá trị không đúng, phải là bội số của {1}",
            "email": "Trường này chưa đúng định dạng email",
            "url": "Trường này chưa đúng định dạng địa chỉ URL",
            "date": "Trường này chưa đúng định dạng (hoặc giá trị) ngày tháng (yyyy-mm-dd)",
            "datetime": "Trường này chưa đúng định dạng (hoặc giá trị) ngày tháng và giờ phút (yyyy-mm-dd hh:mm:ss).",
            "number": "Trường này chưa đúng định dạng số",
            "digits": "Trường này chưa đúng định dạng chỉ gồm các chữ số.",
            "equalTo": "Trường này chưa đúng do không giống với trường {1}",
            "file.type": "Kiểu của file chưa đúng",
            "file.size": "Kích thước của file lớn hơn {1}",
            "unique": "Trường này không được trùng nhau.",
            "foreign_key": "Giá trị này không hợp lệ.",
            "regexp": "Trường này định dạng chưa đúng.",
        }

        name = self.data.get("name", "").strip().lower()
        if not name:
            return ""

        field_messages = []
        file_messages = []

        type = self.data.get("type")
        type_value = type.strip()
        if type_value == "date":
            field_messages.append(f"\t\t\t\t\t'{type_value}': '{messages[type_value]}'")
        if type_value == "datetime":
            field_messages.append(f"\t\t\t\t\t'{type_value}': '{messages[type_value]}'")

        for attr in self.validated_attributes:
            value = self.data.get(attr)
            if not value or not value.strip():
                continue

            is_true = value.strip() == "1" or value.strip().lower() == "true"
            if attr in {"not_null", "unique", "email", "url", "date", "number", "digits"}:
                if is_true:
                    field_messages.append(f'\t\t\t\t\t"{attr}" : "{messages[attr]}"')
            elif attr in {"file.size", "file.type"} and self.is_file():
                file_messages.append(f'\t\t\t\t\t"{attr}" : "{messages[attr]}"')
            else:
                field_messages.append(f'\t\t\t\t\t"{attr}" : "{messages[attr]}"')

        if not field_messages:
            return ""

        result = f"\t\t\t\t'{name}': {{\n" + ",\n".join(field_messages) + "\n\t\t\t\t}"
        if file_messages:
            result += f",\n\t\t\t\t'f{name}': {{\n" + ",\n".join(file_messages) + "\n\t\t\t\t}"
        return result

    def generate_linked_table(self):
        """
        Trả về tên trường nếu trường đó có liên kết foreign key.

        - Thực hiện:
            + Kiểm tra xem trong `self.data` có tồn tại giá trị `foreign_key` hợp lệ (không rỗng).
            + Nếu có, trả về tên trường (`self.data["name"]` đã loại bỏ khoảng trắng).
            + Nếu không có `foreign_key`, trả về chuỗi rỗng.

        - Trả về:
            + Tên trường dạng string nếu là foreign key.
            + Chuỗi rỗng nếu không có liên kết.
        """
        fk = self.data.get("foreign_key", "")
        if fk and fk.strip():
            return self.data.get("name", "").strip()
        return ""


class ControllerGenerator:
    """
    Lớp `ControllerGenerator` dùng để sinh tự động mã nguồn controller (API) cho một module trong Odoo,
    dựa trên cấu trúc metadata được nạp từ file XML đã được phân tích cú pháp thành dictionary (`xml_dict`).

    ### Mục đích:
    - Tự động hóa việc sinh mã controller Odoo phục vụ cho hệ thống CRUD backend.
    - Đồng thời sinh các cấu hình kiểm tra (rules), thông báo lỗi (messages), định nghĩa các trường số, file, khóa ngoại, v.v.
    - Giảm lặp lại khi viết tay controller cho từng model.

    ### Khởi tạo:
    - `__init__(self, xml_dict)`: Nhận vào `xml_dict` (thường được parse từ file XML cấu hình model) và trích xuất:
        * `module_name`, `class_name`: thông tin định danh module
        * `field_data`: danh sách các trường (fields) từ metadata
        * `search_fields`, `default_order_fields`
        * Các danh sách: `field_list`, `unique_list`, `field_number_list`, `file_list`, `fk_list` dùng để build controller và validator

    ### Các phương thức chính:
    - `generate_model_update()`: Sinh mã dictionary cập nhật dữ liệu từ bản ghi `record`.
    - `generate_rules()`: Sinh chuỗi rule kiểm tra đầu vào dựa trên field metadata.
    - `generate_messages()`: Sinh chuỗi thông báo lỗi tương ứng với các rule.
    - `generate_linked_list()`: Trích xuất danh sách tên trường có liên kết khóa ngoại.
    - `generate_controller()`: Tổ hợp toàn bộ thông tin trên và sinh ra nội dung file Python controller hoàn chỉnh cho Odoo.

    ### Đầu ra:
    - Mỗi hàm trả về một chuỗi Python code có thể trực tiếp ghi ra file `.py` để đưa vào hệ thống Odoo.
    - Đặc biệt `generate_controller()` có thể dùng để sinh full nội dung controller class, sẵn sàng cho CRUD logic.

    ### Ví dụ sử dụng:
    ```python
    with open("metadata.xml") as f:
        xml_dict = xmltodict.parse(f.read())

    gen = ControllerGenerator(xml_dict)
    code = gen.generate_controller()

    with open("controllers/generated_api.py", "w", encoding="utf-8") as f:
        f.write(code)
    ```

    ### Ghi chú:
    - Lớp này phụ thuộc vào class `Field` để xử lý logic cho từng trường riêng lẻ.
    - Mỗi phần xử lý đều có xử lý ngoại lệ để đảm bảo không crash toàn bộ tiến trình sinh mã.
    - Hữu ích trong các hệ thống sinh mã tự động (code generation, low-code backend, scaffold tool).
    """

    def __init__(self, xml_dict):
        try:
            try:
                self.module_name = xml_dict["root"]["model"]
                self.class_name = self.module_name.title()
                self.search_fields = xml_dict["root"].get("searchable_list", "") or ""
                self.default_order_fields = xml_dict["root"].get("default_order", "") or ""
                field_data = xml_dict["root"]["fields"]["field"]
                self.field_data = field_data if isinstance(field_data, list) else [field_data]
            except Exception:
                raise Exception("Thuộc tính type không thể thiếu.")

            self.field_list = []
            self.field_number_list = {}
            self.unique_list = []
            self.file_list = []
            self.fk_list = []

            for field in self.field_data:
                if field is None:
                    continue

                field_name = Field(field).get_name()
                self.field_list.append(field_name)

                if field.get("unique", "").strip().lower() in ["1", "t", "c", "đ"]:
                    self.unique_list.append(field_name)

                field_type = field.get("type")
                if field_type:
                    type_str = field_type.strip().lower()
                    if type_str in ["int", "smallint", "integer", "bool", "float", "double"]:
                        self.field_number_list[field_name] = "float" if type_str in ["float", "double"] else "int"
                    elif type_str in ["file", "image"]:
                        self.file_list.append(field_name)
                else:
                    raise Exception("Thuộc tính type không thể thiếu.")

                if field.get("foreign_key", "").strip().lower() in ["1", "t", "c", "đ"]:
                    self.fk_list.append(field_name)

            self.field_list.append("active")
            self.field_number_list["active"] = "int"

        except Exception as e:
            print("Lỗi khởi tạo GenerateController: " + str(e))
            return None

    def generate_model_update(self):
        """
        Sinh ra đoạn mã cập nhật dữ liệu từ bản ghi (`record`) vào một dictionary theo cấu trúc field của model.

        - Thực hiện:
            + Duyệt qua danh sách `self.field_data` — mỗi phần tử là một dict biểu diễn thông tin field.
            + Bỏ qua các field không có tên hợp lệ hoặc field có `auto_generate = "1"`.
            + Với mỗi field:
                * Nếu field thuộc danh sách `unique_list` → tạo giá trị mới bằng cách thay số trong chuỗi cũ bằng `maxID` (dùng regex).
                * Nếu là trường foreign key → gán `.id` nếu có, ngược lại là `None`.
                * Nếu không thuộc loại đặc biệt → gán trực tiếp `record.<field_name>`.

        - Trả về:
            + Chuỗi biểu diễn dictionary mapping dạng:
                ```python
                'field1': record.field1,
                'field2': record.field2.id if record.field2.id else None,
                'code': re.sub(r"\\([0-9]+\\)", "", record.code) + '(' + str(maxID) + ')',
                ...
                ```
            + Các dòng được nối bởi `, \n` để dễ nhúng vào hàm `write({ ... })` hoặc `update({ ... })`.

        - Ghi chú:
            + Hàm này dùng để sinh tự động phần cập nhật dữ liệu giữa các bản ghi, ví dụ khi clone bản ghi cũ sang mới với giá trị cập nhật.
            + Biến `maxID` được giả định có sẵn trong phạm vi sử dụng (ngoài hàm).
        """
        lines = []
        for field in self.field_data:
            if not field:
                continue
            field_name = field.get("name", "").strip()
            if not field_name:
                continue
            line = ""
            field_lower = field_name.lower()

            if field_name in self.unique_list:
                line += f"\t\t\t'{field_lower}': re.sub(r\"\\([0-9]+\\)\", \"\", record.{field_lower}) + '(' + str(maxID) + ')'"
            else:
                if field.get("auto_generate") == "1":
                    continue
                line += f"\t\t\t'{field_lower}': record.{field_lower}"
                if field.get("foreign_key", "").strip():
                    line += f".id if record.{field_lower}.id else None"
            lines.append(line)
        return ", \n".join(lines)

    def generate_rules(self):
        """
        Sinh ra chuỗi các rule validation cho toàn bộ các field trong `self.field_data`.

        - Thực hiện:
            + Duyệt qua từng field trong `self.field_data`:
                * Bỏ qua field trống hoặc không có `name`, hoặc có `name` là `"id"`.
                * Với mỗi field hợp lệ, tạo đối tượng `Field` và gọi `generate_rules(module_name)` để sinh rule cho field đó.
                * Nếu rule trả về không rỗng, thêm vào danh sách rule.
            + Nối các rule lại bằng dấu `, \n` để tạo thành block rule hoàn chỉnh.

        - Trả về:
            + Chuỗi các block rule (ở định dạng giống JSON hoặc Python dict).
            + Trả về `None` nếu có lỗi xảy ra trong quá trình xử lý (và in ra lỗi qua `print`).

        - Ghi chú:
            + Hàm này dựa vào class `Field` có phương thức `generate_rules(...)` để xử lý từng field cụ thể.
            + Biến `self.module_name` được truyền vào mỗi field để phục vụ việc sinh rule liên quan đến `unique`.
        """
        try:
            rules = []
            for field in self.field_data:
                if not field:
                    continue
                name = field.get("name", "").strip()
                if not name or name == "id":
                    continue
                rule = Field(field).generate_rules(self.module_name)
                if rule:
                    rules.append(rule)
            return ", \n".join(rules)
        except Exception as e:
            print("Lỗi sinh rules: " + str(e))
            return None

    def generate_messages(self):
        """
        Sinh ra chuỗi các thông báo lỗi (messages) cho toàn bộ field trong `self.field_data`.

        - Thực hiện:
            + Duyệt qua từng field trong `self.field_data`:
                * Bỏ qua field trống hoặc có `name` là `"id"`.
                * Với mỗi field hợp lệ, tạo đối tượng `Field` và gọi `generate_messages()` để sinh message cho field đó.
                * Nếu message trả về không rỗng, thêm vào danh sách messages.
            + Nối tất cả message lại bằng dấu `, \n` để tạo thành block message hoàn chỉnh.

        - Trả về:
            + Chuỗi các message dạng JSON-like, sẵn sàng để nhúng vào phần cấu hình validation.
            + Trả về `None` nếu có lỗi xảy ra, đồng thời in ra lỗi bằng `print`.

        - Ghi chú:
            + Phụ thuộc vào class `Field` có phương thức `generate_messages()` để xử lý từng field cụ thể.
            + Các thông báo sinh ra có thể chứa placeholder như `{1}`, `{2}` để frontend thay thế khi hiển thị.
        """
        try:
            messages = []
            for field in self.field_data:
                if not field:
                    continue
                name = field.get("name", "").strip()
                if name == "id":
                    continue
                msg = Field(field).generate_messages()
                if msg:
                    messages.append(msg)
            return ", \n".join(messages)
        except Exception as e:
            print("Lỗi sinh messages: " + str(e))
            return None

    def generate_linked_list(self):
        """
        Sinh ra danh sách tên các trường có liên kết khóa ngoại (foreign key) dưới dạng chuỗi.

        - Thực hiện:
            + Duyệt qua toàn bộ `self.field_data`, với mỗi field:
                * Tạo đối tượng `Field(f)` và gọi `generate_linked_table()` để kiểm tra có liên kết hay không.
                * Chỉ giữ lại các tên trường hợp lệ (khác rỗng).
            + Nếu có trường liên kết, nối lại thành chuỗi `'field1, field2, ...'`.
            + Nếu không có, trả về chuỗi rỗng.

        - Trả về:
            + Chuỗi `'field1, field2, ...'` nằm trong dấu nháy đơn nếu có liên kết.
            + Trả về chuỗi rỗng nếu không có trường nào liên kết.

        - Ghi chú:
            + Dùng để tổng hợp danh sách các trường cần xử lý mối quan hệ (có foreign key), phục vụ sinh code hoặc thiết kế schema.
            + Nếu xảy ra lỗi trong quá trình xử lý, sẽ in lỗi ra console và trả về chuỗi rỗng.
        """
        try:
            tables = [Field(f).generate_linked_table() for f in self.field_data if f]
            tables = [t for t in tables if t]
            return f"'{', '.join(tables)}'" if tables else ""
        except Exception as e:
            print("Lỗi tạo linked list: " + str(e))
            return ""

    def generate_controller(self):
        """
        Sinh mã Python cho controller API của một module Odoo, dựa trên thông tin metadata được cấu hình trong đối tượng hiện tại.

        - Thực hiện:
            + Chuẩn hóa danh sách `search_fields` thành list dạng `["field1", "field2", ...]`.
            + Gọi `generate_linked_list()` để lấy danh sách các trường liên kết foreign key (định dạng `'field1', 'field2'`).
            + Chèn toàn bộ các phần thông tin vào mẫu template controller:
                * `modelName`, `Alias2Fields`, `Fields2Labels`, `searchFields`
                * `fieldList`, `numberFields`, `fileList`, `foreignFields`
                * `validator.rules` và `validator.messages` sinh từ `generate_rules()` và `generate_messages()`
                * Hàm `_generateObject()` sinh từ `generate_model_update()` để tạo dictionary từ bản ghi

        - Trả về:
            + Chuỗi mã Python hoàn chỉnh cho một file controller, sẵn sàng ghi vào file `.py` trong Odoo module.

        - Ví dụ:
            Tên class được sinh ra sẽ là `<ClassName>_API`, kế thừa từ `Nagaco_Controller`, có cấu hình validator và các hàm xử lý dữ liệu chuẩn hóa.

        - Ghi chú:
            + Phương thức này phục vụ mục tiêu sinh mã tự động cho backend API theo metadata định nghĩa.
            + Đầu ra nên được ghi ra file `.py` để sử dụng trong Odoo project.
        """

        field_names = [f'"{f.strip()}"' for f in self.search_fields.split(",") if f.strip()]
        linked_fields = self.generate_linked_list().replace("'", "").replace(" ", "").split(",")
        linked_fields_str = "', '".join(linked_fields)

        content = f"""# -*- coding: utf-8 -*-
import json
import re
from odoo.http import Response, request
from .base_class.nagaco_controller import Nagaco_Controller

from ..helper.validator import Validator
from ..models.{self.module_name}_model import {self.class_name}Alias2Fields, {self.class_name}Fields2Labels
from ..helper.serializer import Serializer
from ..helper.normalizer import Normalizer

class {self.class_name}_API(Nagaco_Controller):
    def __init__(self):
        Nagaco_Controller.__init__(self)
        self.modelName = "{self.module_name}"        
        self.Alias2Fields = {self.class_name}Alias2Fields
        self.Fields2Labels = {self.class_name}Fields2Labels
        self.searchFields = [{', '.join(field_names)}]
        self.fieldList = ["{'", "'.join(self.field_list)}"]
        self.numberFields = {self.field_number_list}
        self.fileList = {self.file_list}
        self.foreignFields = ['{linked_fields_str}']
        self.validator = Validator(
            rules={{
                {self.generate_rules()}
            }},
            messages={{
                {self.generate_messages()}
            }}
        )

    def _generateObject(self, record, maxID=1):
        return {{
{self.generate_model_update()}
        }}
"""

        return content
