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
    def __init__(self, field_data):
        self.data = field_data
        self.validated_attributes = ["not_null", "min_length", "max_length", "range_length", "min", "max", "range", "step", "email", "url", "date", "number", "digits", "equalTo", "file.type", "file.size", "unique", "foreign_key", "regexp"]
        self.field_list = []
        self.number_field_list = []

    def get_name(self):
        if "name" in self.data and self.data["name"] is not None:
            return self.data["name"].strip().lower()
        else:
            return ""

    def is_number(self):
        if "type" in self.data and self.data["type"] is not None:
            type = self.data["type"].strip().lower()
        else:
            type = ""
        return type in ["int", "smallint", "float", "double"]

    def is_file(self):
        if "type" in self.data and self.data["type"] is not None:
            type = self.data["type"].strip().lower()
        else:
            type = ""
        return type in ["file", "image"]

    def generate_rules(self, module_name=None) -> str:
        """
        Sinh ra rule cho field dựa vào self.data và self.validated_attributes
        """
        name = self.data.get("name", "").strip().lower()
        if not name:
            return ""

        rules = []
        file_rules = []

        for attr in self.validated_attributes:
            raw_value = self.data.get(attr)
            if not raw_value or not raw_value.strip():
                continue

            value = raw_value.strip()
            is_true = value == "1" or value.lower() == "true"

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
            elif attr in {"file.size", "file.type"} and self.isFile():
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

    def generate_model_field(self):
        args = []
        field_type = ""

        for field, raw in self.data.items():
            value = raw.strip() if raw else ""
            match field:
                case "type":
                    field_type = f"fields.{TypeAlias[value].value}"
                case "unique":
                    if value == "1" or value.lower() == "true":
                        args.append("unique=True")
                case "not_null":
                    if value == "1" or value.lower() == "true":
                        args.append("required=True")
                case "max_length":
                    args.append(f"size={value}")
                case "foreign_key":
                    parts = value.split(",")
                    if len(parts) >= 3:
                        args.append(f"size='{parts[0]}', '{parts[2]}'")
                case "label":
                    args.append(f"string='{value}'")
                case "default_value":
                    args.append(f"default={value}")

        return f"{self.data['name']} = {field_type}({', '.join(args)})"

    def generate_model_constraint(self):
        constraints = []
        name = self.data.get("name", "").strip().lower()

        for field, raw in self.data.items():
            value = raw.strip() if raw else ""
            match field:
                case "unique":
                    if value == "1" or value.lower() == "true":
                        constraints.append(f"('{name}_unique', 'unique({name})', 'Giá trị đã có rồi!')")
                case "primary_key":
                    if value == "1" or value.lower() == "true":
                        constraints.append(f"('{name}_unique', 'unique({name})', 'Giá trị khóa không được trùng nhau!')")

        return ",".join(constraints)

    def generate_linked_table(self):
        fk = self.data.get("foreign_key", "")
        if fk and fk.strip():
            return self.data.get("name", "").strip()
        return ""


class ControllerGenerator:
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

    def generate_searchable_list(self):
        names = [n.strip() for n in self.search_fields.replace(" ", "").split(",") if n.strip()]
        result = []
        if len(names) > 1:
            result = [f"('{n}', operator, f\"%{{search}}%\")" for n in names]
            result = ["'|'"] * (len(result) - 1) + result
            return ",".join(result)
        elif names:
            return f"('{names[0]}', operator, f\"%{{search}}%\")"
        return ""

    def generate_model_update(self):
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
        try:
            tables = [Field(f).generate_linked_table() for f in self.field_data if f]
            tables = [t for t in tables if t]
            return f"'{', '.join(tables)}'" if tables else ""
        except Exception as e:
            print("Lỗi tạo linked list: " + str(e))
            return ""

    def generate_sort_field(self):
        return (
            """
                if len(query) > 0:
                    records = records.sorted(key=lambda r: len(r.code))
            """
            if "code" in self.search_fields
            else ""
        )

    def generate_controller(self):

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
