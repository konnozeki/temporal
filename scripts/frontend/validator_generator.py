import json


class ValidatorGenerator:
    def __init__(self, xml_dict):
        self.xml_dict = xml_dict
        self.model_name = (xml_dict.get("root", {}).get("model", "") or "").strip()
        self.validated_attributes = [
            "not_null",
            "min_length",
            "max_length",
            "range_length",
            "min",
            "max",
            "range",
            "step",
            "email",
            "url",
            "date",
            "number",
            "digits",
            "equalTo",
            "file.type",
            "file.size",
            "unique",
            "foreign_key",
            "regexp",
        ]
        self.message_templates = {
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
            "json": "Trường này chưa đúng định dạng JSON.",
            "reference": "Giá trị tham chiếu này không hợp lệ.",
        }

    @staticmethod
    def _is_truthy(value: str) -> bool:
        return value.lower() in {"1", "true", "t", "c", "đ"}

    @staticmethod
    def _is_file_type(field_type: str) -> bool:
        return field_type in {"file", "image"}

    def _normalize_fields(self):
        fields = self.xml_dict.get("root", {}).get("fields", {}).get("field", [])
        return fields if isinstance(fields, list) else [fields]

    def _generate_rules_for_field(self, field):
        name = (field.get("name", "") or "").strip().lower()
        if not name:
            return {}, {}

        field_type = (field.get("type", "") or "").strip().lower()
        is_file_field = self._is_file_type(field_type)

        rules = {}
        file_rules = {}

        if field_type in {"date", "datetime", "json"}:
            rules[field_type] = True
        if field_type == "reference":
            rules[field_type] = self.model_name

        for attr in self.validated_attributes:
            raw_value = field.get(attr)
            if raw_value is None:
                continue
            value = str(raw_value).strip()
            if not value:
                continue

            is_true = self._is_truthy(value)
            if attr in {"min", "max", "min_length", "max_length", "step"}:
                try:
                    rules[attr] = int(float(value))
                except ValueError:
                    continue
            elif attr == "regexp":
                rules[attr] = value
            elif attr == "not_null" and is_true:
                rules["required"] = True
            elif attr == "unique" and is_true:
                rules[attr] = f"{self.model_name}.{name}"
            elif attr in {"email", "url", "date", "number", "digits"} and is_true:
                rules[attr] = True
            elif attr == "equalTo":
                rules[attr] = value
            elif attr == "foreign_key":
                rules[attr] = value.replace(" ", "").replace(",", ".")
            elif attr in {"file.size", "file.type"} and is_file_field:
                file_rules[attr] = value
            elif is_true:
                rules[attr] = value

        return rules, file_rules

    def _generate_messages_for_field(self, field):
        name = (field.get("name", "") or "").strip().lower()
        if not name:
            return {}, {}

        field_type = (field.get("type", "") or "").strip().lower()
        is_file_field = self._is_file_type(field_type)

        messages = {}
        file_messages = {}

        if field_type in {"date", "datetime", "json", "reference"}:
            messages[field_type] = self.message_templates[field_type]

        for attr in self.validated_attributes:
            raw_value = field.get(attr)
            if raw_value is None:
                continue
            value = str(raw_value).strip()
            if not value:
                continue

            is_true = self._is_truthy(value)
            if attr in {"not_null", "unique", "email", "url", "date", "number", "digits"}:
                if is_true:
                    messages[attr] = self.message_templates[attr]
            elif attr in {"file.size", "file.type"} and is_file_field:
                file_messages[attr] = self.message_templates[attr]
            else:
                messages[attr] = self.message_templates[attr]

        return messages, file_messages

    def generate(self):
        rules_payload = {}
        messages_payload = {}
        fields = self._normalize_fields()

        for field in fields:
            if not field:
                continue
            field_name = (field.get("name", "") or "").strip().lower()
            if not field_name or field_name == "id":
                continue

            field_rules, file_rules = self._generate_rules_for_field(field)
            field_messages, file_messages = self._generate_messages_for_field(field)

            if field_rules:
                rules_payload[field_name] = field_rules
            if file_rules:
                rules_payload[f"f{field_name}"] = file_rules
            if field_messages:
                messages_payload[field_name] = field_messages
            if file_messages:
                messages_payload[f"f{field_name}"] = file_messages

        return json.dumps(
            {"rules": rules_payload, "messages": messages_payload},
            ensure_ascii=False,
            indent=2,
        )
