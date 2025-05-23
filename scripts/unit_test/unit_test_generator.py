from typing import Dict, Union, Any


class UnitTestGenerator:
    def __init__(self, xml_dict: Dict[str, Any]):
        self.xml_fields = xml_dict.get("root", {}).get("fields", {}).get("field", [])
        # Column list cho các phương thức get
        self.column_list = [field["alias"].strip() for field in self.xml_fields if field.get("alias")]
        self.fields = [field["name"].strip() for field in self.xml_fields if field.get("name")]
        # Criteria cho validator
        self.criteria = {field: {} for field in self.fields}

        # Các thành phần cho các phương thức get.
        self.order_list = xml_dict.get("root", {}).get("default_order").strip().split(",")
        self.order_alias_list = [field["alias"].strip() for field in self.xml_fields if "alias" in field.keys() and field["name"] in self.order_list]

        self.max_length_fields = {}
        self.min_length_fields = {}
        self.require_fields = []
        self.foreign_fields = []
        self.unique_fields = []
        self.email_fields = []
        self.numeric_fields = []
        self.boolean_fields = []
        self.datetime_fields = []
        self.string_fields = []

    def create_criteria(self):
        for field in self.xml_fields:
            # Lấy tên và các thuộc tính có thể có của field
            name = field.get("name", "").strip()
            max_length = field.get("max_length", "").strip()
            min_length = field.get("min_length", "").strip()
            not_null = field.get("not_null", "").strip()
            foreign_key = field.get("foreign_key", "").strip()
            unique = field.get("unique", "").strip()
            email = field.get("email", "").strip()
            field_type = field.get("type", "").strip()

            # Kiểm tra và lưu max_length nếu có và hợp lệ
            if max_length.isdecimal():
                self.criteria[name]["max_length"] = int(max_length)

            # Kiểm tra và lưu min_length nếu có và hợp lệ, nếu không thì mặc định 0
            if min_length.isdecimal():
                self.criteria[name]["min_length"] = int(min_length)
            else:
                self.criteria[name]["min_length"] = 0

            # Kiểm tra yêu cầu không null
            if not_null == "1":
                self.criteria[name]["required"] = True

            # Kiểm tra khóa ngoại
            if foreign_key:
                reference_model = foreign_key.split(",")[0].strip()
                self.criteria[name]["foreign_key"] = reference_model

                # Nếu đã có max_length thì loại bỏ vì không còn cần thiết với foreign key
                if "max_length" in self.criteria[name].keys():
                    del self.criteria[name]["max_length"]

            # Kiểm tra duy nhất
            if unique == "1":
                self.criteria[name]["unique"] = True

            # Kiểm tra email
            if email == "1":
                self.criteria[name]["email"] = True

            # Kiểm tra kiểu số
            if field_type in ["integer", "float", "double"]:
                self.criteria[name]["number"] = True

            # Kiểm tra kiểu ngày giờ
            if field_type in ["date", "datetime"]:
                self.criteria[name]["date"] = True

            # Kiểm tra kiểu chuỗi
            if field_type in ["varchar", "text"]:
                self.string_fields.append(name)

                # Kiểm tra kiểu boolean
            if field_type == "bool":
                self.boolean_fields.append(name)
