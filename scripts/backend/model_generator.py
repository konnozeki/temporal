from enum import Enum
import os
from config import *
import re


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
    # file = 'File'
    file = "Char"
    image = "Char"
    smallint = "Integer"


class ModelGenerator:
    """
    Lớp `ModelGenerator` đại diện cho bộ sinh mã định nghĩa model Odoo từ metadata (thường đến từ file XML),
    cho phép tự động hóa toàn bộ quá trình tạo file `model.py` gồm class model, ràng buộc, alias, nhãn và kiểm tra xóa.

    ### Mục đích:
    - Tự động sinh ra file model.py đầy đủ cho một model trong Odoo từ cấu trúc XML chuẩn hóa.
    - Chuẩn hóa quá trình xây dựng hệ thống dữ liệu, giảm thao tác thủ công và sai sót trong định nghĩa model.
    - Tích hợp tốt với hệ thống sinh mã toàn cục (module scaffolding, UI generator...).

    ### Thuộc tính:
    - `self.xml_dict` (List[dict]): Danh sách các field sau khi parse từ XML (đã chuẩn hóa về list).
    - `self.model_name` (str): Tên kỹ thuật của model, dùng cho `_name`.
    - `self.class_name` (str): Tên class Python (viết hoa) tương ứng với `model_name`.
    - `self.number_types` (List[str]): Danh sách các kiểu dữ liệu dạng số (int, float, bool...) để xử lý default.
    - `self.approval_list` (List[str]): Danh sách các model cần `active=False` mặc định.
    - `self.allow_null` (List[str]): Danh sách kiểu được phép để default rỗng (`date`, `datetime`...).

    ### Các phương thức chính:
    - `create_column_alias()`: Sinh Enum ánh xạ alias ngắn → tên field đầy đủ (bao gồm cả trường con trong khóa ngoại).
    - `create_column_label()`: Sinh Enum ánh xạ field → label để hiển thị hoặc báo lỗi.
    - `create_constraints()`: Sinh `_sql_constraints` cho các trường có unique hoặc primary key.
    - `create_model()`: Sinh toàn bộ phần định nghĩa class model, bao gồm các field và kiểu dữ liệu.
    - `create_can_delete()`: Sinh field `can_delete` và logic `_compute_can_delete_by_view()` kiểm tra khả năng xóa bản ghi.
    - `generate_model()`: Tổ hợp toàn bộ các thành phần trên thành nội dung hoàn chỉnh cho file `model.py`.

    ### Ghi chú:
    - Class này **không thực hiện việc ghi file**, mà chỉ sinh ra nội dung dạng chuỗi.
    - Có thể dùng kết hợp với generator view/controller để sinh trọn bộ module backend.
    - Yêu cầu các giá trị như `TypeAlias` và `CAN_DELETE_DEFAULT` phải được định nghĩa trước trong môi trường sử dụng.
    """

    def __init__(self, xml_dict):
        try:
            fields = xml_dict["root"]["fields"]["field"]
            self.xml_dict = fields if isinstance(fields, list) else [fields]

            self.model_name = xml_dict["root"]["model"]
            self.class_name = self.model_name.replace("_", " ").title().replace(" ", "_")

            self.number_types = ["int", "integer", "smallint", "float", "double", "bool"]
            self.approval_list = ["nagaco_color", "nagaco_size", "nagaco_fit", "nagaco_supplier", "nagaco_article"]
            self.allow_null = ["date", "datetime"]
        except Exception as e:
            print("Định dạng tệp XML chưa đúng:", e)

    def create_column_alias(self):
        """
        Tạo class Enum ánh xạ alias (tên rút gọn) sang tên đầy đủ của field trong model.

        - Mục đích:
            + Tạo các alias ngắn gọn, không trùng lặp, để sử dụng trong phần `filter`, `sort`, hoặc query động.
            + Hỗ trợ alias hóa cả các trường thường lẫn khóa ngoại (`foreign_key`), bao gồm cả các trường con.

        - Thực hiện:
            + Với mỗi field trong `self.xml_dict`:
                * Dùng `alias` nếu có, hoặc tự động sinh từ 3 ký tự đầu của `name`.
                * Đảm bảo alias không trùng thông qua hàm `get_unique_alias`.
                * Nếu là khóa ngoại:
                    - Tạo alias chính cho field gốc.
                    - Tạo thêm các alias phụ cho các trường con (ví dụ: `category.name` → `catna`).
            + Cuối cùng thêm các alias mặc định:
                * `'acti' = 'active'`
                * `'wd' = 'write_date'`
                * `'cd' = 'can_delete'`

        - Trả về:
            + Chuỗi định nghĩa class Enum (ví dụ: `class ProductAlias2Fields(Enum): ...`) với các dòng alias.

        - Ghi chú:
            + Sử dụng `reserved_keywords` để tránh trùng alias.
            + Nếu không thể tìm được alias hợp lệ sau 100 lần thử → raise lỗi.
            + Hàm phụ `get_unique_alias(base, existing)` giúp đảm bảo tính duy nhất trong tập alias.

        - Ví dụ đầu ra:
            ```python
            class ProductAlias2Fields(Enum):
                nam = 'name'
                cat = 'category_id'
                catna = 'category_id.name'
                acti = 'active'
                wd = 'write_date'
                cd = 'can_delete'
            ```
        """
        reserved_keywords = {"and", "as", "assert", "async", "await", "break", "class", "continue", "def", "del", "elif", "else", "except", "False", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "None", "nonlocal", "not", "or", "pass", "raise", "return", "True", "try", "while", "with", "yield", "cd"}

        def get_unique_alias(base, existing):
            """
            Tạo alias không trùng với từ khóa đã có.
            - base: Tên gốc để tạo alias.
            - existing: Tập hợp các alias đã tồn tại.
            - Trả về alias duy nhất.
            - Nếu không tìm thấy alias hợp lệ sau 100 lần thử thì raise lỗi.
            """
            if base not in existing:
                return base
            for i in range(1, 100):
                candidate = f"{base}{i}"
                if candidate not in existing:
                    return candidate
            raise Exception(f"Không tìm được alias hợp lệ cho {base}")

        try:
            aliases = []
            enum_header = f"class {self.class_name}Alias2Fields(Enum):"

            for field in self.xml_dict:
                if not field:
                    continue

                field_type = field.get("type", "").strip().lower()
                field_name = field.get("name", "").strip().lower()
                foreign_key = field.get("foreign_key", "").strip()

                if not field_type or not field_name:
                    raise ValueError("Các mục 'name' và 'type' là bắt buộc.")

                base_alias = field.get("alias", field_name[:3]).strip().lower()
                alias = get_unique_alias(base_alias, reserved_keywords)
                reserved_keywords.add(alias)

                if foreign_key:
                    parts = [p.strip() for p in foreign_key.split(",")]
                    if len(parts) < 3:
                        raise ValueError("Định dạng 'foreign_key' phải là '<tên bảng>,<khóa>,<nhãn>'.")

                    aliases.append(f"\t{alias} = '{field_name}'")

                    for key_part in parts[1:]:
                        sub_alias = get_unique_alias(f"{alias}{key_part[:2].lower()}", reserved_keywords)
                        reserved_keywords.add(sub_alias)
                        aliases.append(f"\t{sub_alias} = '{field_name.lower()}.{key_part.lower()}'")
                else:
                    aliases.append(f"\t{alias} = '{field_name}'")

            # Alias mặc định thêm cuối
            aliases.append("\tacti = 'active'")
            aliases.append("\twd = 'write_date'")
            aliases.append("\tcd = 'can_delete'")

            return enum_header + "\n" + "\n".join(aliases)

        except Exception as e:
            print("Đã xảy ra lỗi khi tạo các alias cho model. Thông tin về lỗi:", str(e))
            return ""

    def create_column_label(self):
        """
        Phương thức này cho phép tạo các nhãn cho các cột theo các thông tin trong self.xmlDict và self.modelName.
        - Các tham số: Không có
        - Các kết quả trả về:
            + Xâu cho phép sinh ra khai báo các nhãn cho model.
            + Ngược lại thì thông báo lỗi.
        - Các tình huống:
            1. Nếu một trong các thuộc tính name, type, label bị thiếu thì dừng và báo lỗi.
            2. Nếu xảy ra lỗi bất kỳ thì phải bắt được và đưa ra thông báo đã gặp lỗi.
        """
        str_fields_to_label = ""
        try:
            array_label = []
            str_fields_to_label = f"class {self.class_name}Fields2Labels(Enum):"

            for idx, item in enumerate(self.xml_dict):
                if not item:
                    continue

                item_type = item.get("type", "").strip().lower() if item.get("type") else ""
                item_name = item.get("name", "").strip().lower() if item.get("name") else ""
                item_label = item.get("label", "").strip() if item.get("label") else ""

                if not item_name:
                    raise Exception(f"Thiếu thuộc tính 'name' tại vị trí field thứ {idx+1}.")
                if not item_type:
                    raise Exception(f"Thiếu thuộc tính 'type' cho trường '{item_name}'.")
                if not item_label:
                    raise Exception(f"Thiếu thuộc tính 'label' cho trường '{item_name}'.")

                # Chuẩn hóa nhãn: gộp các khoảng trắng, viết hoa chữ cái đầu
                item_label = re.sub(r"\s+", " ", item_label).strip().capitalize()

                array_label.append(f"\t{item_name} = '{item_label}'")

            # Các nhãn mặc định
            array_label.append(f"\tactive = 'Trạng thái'")
            array_label.append(f"\twrite_date = 'Thời gian cập nhật cuối cùng'")
            array_label.append(f"\tcan_delete = 'Có thể xóa'")

        except Exception as e:
            print("Đã xảy ra lỗi khi tạo các nhãn cho model. Thông tin về lỗi: " + str(e))

        return str_fields_to_label + "\n" + "\n".join(array_label)

    def create_constraints(self):
        """
        Phương thức này tạo xâu khai báo các ràng buộc (_sql_constraints) cho model dựa trên self.xmlDict.
        - Kết quả trả về:
            + Xâu khai báo các ràng buộc cho model nếu có.
            + Nếu xảy ra lỗi thì in thông báo lỗi và trả về chuỗi rỗng.
        - Các tình huống xử lý:
            1. Nếu thiếu thuộc tính 'name' thì dừng và báo lỗi.
            2. Nếu xảy ra lỗi bất kỳ thì phải bắt được và đưa ra thông báo.
        """
        try:
            constraint_list = []

            for idx, item in enumerate(self.xml_dict):
                if not item:
                    continue

                item_name = item.get("name", "").strip().lower()
                item_label = item.get("label", "").strip() if item.get("label") else item_name
                is_unique = str(item.get("unique", "")).strip().lower() in ["1", "true", "c", "đ", "yes", "y"]
                is_primary = str(item.get("primary_key", "")).strip().lower() in ["1", "true"]

                # Bỏ qua nếu không có name hoặc là id
                if not item_name:
                    raise Exception(f"Thiếu thuộc tính 'name' ở phần tử thứ {idx + 1}.")
                if item_name == "id":
                    continue

                if is_unique or is_primary:
                    constraint_list.append(f"\t\t('{item_name}_unique', 'unique({item_name})', '{item_label} already exists!'),\n")

            result = ""
            if constraint_list:
                # Dùng set để loại bỏ trùng lặp nếu có
                result = f"""
    \t_sql_constraints = [
    {"".join(set(constraint_list))}
    \t]
    """
            return result

        except Exception as e:
            print("Đã xảy ra lỗi khi tạo các ràng buộc cho model. Thông tin về lỗi: " + str(e))
            return ""

    def create_model(self):
        """
        Sinh ra chuỗi mã Python định nghĩa một class model Odoo dựa trên metadata từ `self.xml_dict`.

        - Mục đích:
            + Tự động tạo nội dung của một class model kế thừa từ `models.Model` trong Odoo.
            + Dựa trên các thuộc tính được khai báo trong XML (đã parse thành `self.xml_dict`), bao gồm tên trường, kiểu dữ liệu, nhãn, ràng buộc, default, khóa ngoại, compute, v.v.

        - Thực hiện:
            + Khởi tạo phần khai báo class gồm `_name`, `_description`.
            + Duyệt qua từng trường trong `self.xml_dict`:
                * Bỏ qua các field `auto_generate = 1` không có `compute`.
                * Xử lý các loại trường đặc biệt:
                    - Trường có `compute`: sinh `compute=...`, `store=...`.
                    - Trường foreign key: sinh `fields.Many2one` với `ondelete`, `index`, và label.
                    - Trường file/image: ánh xạ sang `fields.Binary`.
                    - Trường thông thường: sinh với các tham số `string`, `required`, `default`, `size`...
                * Tự động sinh thêm trường `active` ở cuối với giá trị default tùy theo module.

        - Trả về:
            + Chuỗi code định nghĩa class model Odoo, có thể được ghi trực tiếp vào file Python.

        - Ghi chú:
            + Phụ thuộc vào các biến như:
                * `self.class_name`: tên class được capitalized từ module.
                * `self.model_name`: tên kỹ thuật của model.
                * `self.approval_list`: danh sách model cần default `active = False`.
                * `TypeAlias`: ánh xạ từ kiểu định nghĩa XML sang Odoo field (ví dụ: "char" → "Char", "int" → "Integer").
                * `self.number_types`, `self.allow_null`: dùng để xác định xử lý `default`.

        - Ví dụ đầu ra:
            ```python
            class Product(models.Model):
                _name = 'product'
                _description = 'Product'

                name = fields.Char(string='Tên sản phẩm', required=True, size=100)
                price = fields.Float(string='Giá', default=0.0)
                category_id = fields.Many2one('category', string='Danh mục', ondelete='no action', index=True)
                active = fields.Boolean(string='Trạng thái', default=1)
            ```
        """
        try:
            model_lines = [f"class {self.class_name}(models.Model):", f"\t_name = '{self.model_name.lower()}'", f"\t_description = '{self.model_name.capitalize()}'"]

            for item in self.xml_dict:
                if not item or (item.get("auto_generate", "").strip() == "1" and "compute" not in item):
                    continue

                name = item.get("name", "").strip().lower()
                if not name:
                    raise Exception("Mục 'name' không thể thiếu.")
                if name == "id":
                    continue

                field_type = item.get("type", "").strip().lower()
                label = item.get("label", "").strip()
                not_null = item.get("not_null", "").strip().lower() in ["1", "true"]
                default = item.get("default_value", "").strip()
                default = "" if default == "\\0" else default
                max_length = item.get("max_length", "").strip()
                range_length = item.get("range_length", "").strip()
                foreign_key = item.get("foreign_key", "").strip()
                compute = item.get("compute")
                ondelete = item.get("ondelete", "no action").strip()

                args = [f"string='{label or name}'"]
                if not_null:
                    args.append("required=True")

                # Handle size
                max_len_val = int(max_length) if max_length.isdigit() else 0
                if range_length.startswith("[") and range_length.endswith("]"):
                    try:
                        _, max_range = map(int, range_length[1:-1].split(","))
                        size_val = min(filter(lambda x: x > 0, [max_len_val, max_range]))
                        if size_val > 0:
                            args.append(f"size={size_val}")
                    except:
                        raise Exception("Định dạng 'range_length' không đúng.")
                elif max_len_val > 0:
                    args.append(f"size={max_len_val}")

                # Handle default
                if not foreign_key and default.upper() != "NULL":
                    if default:
                        default_str = f"default={default}" if field_type in self.number_types else f"default='{default}'"
                        args.append(default_str)
                    elif field_type not in self.allow_null:
                        args.append("default=''")

                # Compute field
                if compute:
                    compute_args = [f"string='{label or name}'", f"compute='{compute['function']}'"]
                    if compute.get("store", "").strip() == "1":
                        compute_args.append("store=True")
                    else:
                        compute_args.append("store=False")
                    field_line = f"\t{name} = fields.{TypeAlias[field_type].value}({', '.join(compute_args)})"
                    model_lines.append(field_line)
                    continue

                # Foreign key
                if foreign_key:
                    fk_parts = [part.strip() for part in foreign_key.split(",")]
                    if len(fk_parts) < 3:
                        raise Exception("Khóa ngoại sai định dạng: '<table>, <field>, <label>'.")
                    related_model = fk_parts[0].lower()
                    fk_args = [f"ondelete='{ondelete}'", "index=True"] + args
                    field_line = f"\t{name} = fields.Many2one('{related_model}', {', '.join(fk_args)})"
                    model_lines.append(field_line)
                    continue

                # File/image
                if field_type in ["file", "image"]:
                    field_line = f"\t{name} = fields.{TypeAlias[field_type].value}({', '.join(args)})"
                    model_lines.append(field_line)
                    continue

                # Normal field
                field_line = f"\t{name} = fields.{TypeAlias[field_type].value}({', '.join(args)})"
                model_lines.append(field_line)

            default_active = 0 if self.model_name in self.approval_list else 1
            model_lines.append(f"\tactive = fields.Boolean(string='Trạng thái', default={default_active})")

            return "\n".join(model_lines)

        except Exception as e:
            print("Đã xảy ra lỗi khi tạo model:", str(e))
            return str(e)

    def create_can_delete(self):
        """
        Sinh ra đoạn mã Python định nghĩa field `can_delete` và logic kiểm tra khả năng xóa bản ghi dựa trên dữ liệu liên kết.

        - Mục đích:
            + Thêm field boolean `can_delete` vào model để xác định xem bản ghi có thể bị xóa hay không.
            + Việc quyết định xóa phụ thuộc vào bảng `<model>_view`, nếu không có bản ghi liên kết → có thể xóa.

        - Thực hiện:
            + Tạo field `can_delete` với `compute='_compute_can_delete_by_view'`, không lưu vào DB (`store=False`).
            + Trong hàm compute:
                * Truy vấn dữ liệu từ bảng view tương ứng (ví dụ `product_view`).
                * Nếu không có dữ liệu liên kết (tổng các cột phụ = 0) → `can_delete = True`.
                * Ngược lại → `can_delete = False`.
                * Nếu truy vấn thất bại → mặc định theo `CAN_DELETE_DEFAULT`.

        - Trả về:
            + Chuỗi mã Python định nghĩa field `can_delete` và hàm compute `_compute_can_delete_by_view`.

        - Ghi chú:
            + Biến `CAN_DELETE_DEFAULT` phải được định nghĩa sẵn trong module config.
            + Dùng trong các hệ thống cần bảo vệ dữ liệu liên kết khỏi thao tác xóa thủ công.
        """
        str_can_delete = f"""
	can_delete = fields.Boolean(string='can delete this field', compute='_compute_can_delete_by_view', store=False)
	def _compute_can_delete_by_view(self):
		for record in self:
			record.can_delete = CAN_DELETE_DEFAULT  # Mặc định theo cấu hình
			try:
				self.env.cr.execute(\"\"\"
					SELECT * FROM {self.model_name.lower()}_view 
					WHERE {self.model_name.lower().replace('nagaco_', '')}_id = %s
				\"\"\", (record.id,))
				rs = self.env.cr.fetchone()
				total = 0
				for (i, e) in enumerate(rs):
					if i > 0:
						total += e
				if total == 0:
					record.can_delete = True # Nếu không có liên kết
				else:
					record.can_delete = False # Nếu có liên kết
			except: 
				pass
"""
        return str_can_delete

    def generate_model(self):
        """
        Tạo nội dung đầy đủ cho file `model.py` trong module Odoo dựa trên metadata đầu vào.

        - Thực hiện:
            + Tổ hợp các thành phần của một model bao gồm:
                * Enum, import cần thiết
                * Alias và nhãn cột (`create_column_alias`, `create_column_label`)
                * Định nghĩa class model (`create_model`)
                * Ràng buộc (`create_constraints`)
                * Trường `can_delete` và hàm compute đi kèm (`create_can_delete`)
            + Trả về chuỗi code Python sẵn sàng để ghi vào file `model.py`.

        - Trả về:
            + Chuỗi mã Python đầy đủ của file model.

        - Ghi chú:
            + Phương thức này không ghi trực tiếp ra file, chỉ trả về nội dung string. Việc ghi file được thực hiện bên ngoài.
            + Nếu bạn cần kiểm tra file tồn tại và ghi thực sự, hãy viết một phương thức khác như `write_model_file(path: str)` để thực thi phần này.
        """

        str_return = f"""
from enum import Enum
from odoo import models, fields
from ..config.config import *

{self.create_column_alias()}
{self.create_column_label()}
{self.create_model()}
{self.create_constraints()}
{self.create_can_delete()}
    """
        return str_return
