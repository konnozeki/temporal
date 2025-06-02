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
        Tạo các alias cho các cột theo thông tin trong self.xml_dict và self.model_name.

        Trả về:
            - Chuỗi chứa class Enum ánh xạ alias ↔ field.

        Gây lỗi:
            - Nếu thiếu 'name' hoặc 'type' trong field.
            - Nếu định dạng foreign_key không hợp lệ.
            - Nếu có lỗi xử lý nội bộ.
        """
        reserved_keywords = {
            "and",
            "as",
            "assert",
            "async",
            "await",
            "break",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "False",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "None",
            "nonlocal",
            "not",
            "or",
            "pass",
            "raise",
            "return",
            "True",
            "try",
            "while",
            "with",
            "yield",
            "cd",
        }

        def get_unique_alias(base, existing):
            """Tạo alias không trùng với từ khóa đã có"""
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
                is_unique = str(item.get("unique", "")).strip().lower() in ["1", "true"]
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
        Tạo chuỗi định nghĩa model Odoo từ self.xml_dict và self.model_name.
        Trả về: chuỗi Python code định nghĩa class model.
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
        Phương thức này cho phép tạo tệp model.
        - Các tham số: Không có
        - Các kết quả trả về:
            + Tệp model.py chứa model của hệ thông.
            + Ngược lại thì thông báo lỗi.
        - Các tình huống:
            1. Nếu tệp model.py đã có thì phải báo lỗi và dừng
            2. Nếu xảy ra lỗi bất kỳ thì phải bắt được và đưa ra thông báo đã gặp lỗi.
            3. Nếu tạo tệp model.py thành công thì đưa ra thông báo thành công.
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
