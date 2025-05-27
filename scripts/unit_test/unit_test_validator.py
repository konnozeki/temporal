from typing import List, Dict, Any, Union
from .unit_test_message import Message
from datetime import datetime
import re


class Validator:

    def handle_create_attribute(self, response: Dict[str, list] = {}, field: str = "", message: Message = "") -> Dict[str, list]:
        if response.get(field, None) is None:
            response[field] = [message]
        elif type(response.get(field)) == list:
            response[field].append(message)
        return response

    def check_foreign_key(self, value: Union[str, int], reference: str) -> bool:
        return value.startswith("{valid")

    def validate(self, fields: List[str] = [], request: Dict[str, Union[str, int, float, bool]] = {}, criteria: Dict[str, Dict[str, Any]] = {}) -> Dict[str, list]:
        response = {}
        passed = True
        for field in fields:
            value = request.get(field, "")
            if field == "id":
                continue
            rule_dict = criteria.get(field, {})
            for rule in rule_dict.keys():
                match rule:
                    case "required":
                        if len(str(value)) == 0:
                            passed = False
                            self.handle_create_attribute(response, field, Message.required.value)
                    case "min_length":
                        if len(str(value)) < rule_dict[rule]:
                            passed = False
                            self.handle_create_attribute(response, field, Message.min_length.value.replace("{1}", f"{rule_dict[rule]}"))
                    case "max_length":
                        if len(str(value)) > rule_dict[rule]:
                            passed = False
                            self.handle_create_attribute(response, field, Message.max_length.value.replace("{1}", f"{rule_dict[rule]}"))
                    case "min":
                        if value < rule_dict[rule]:
                            passed = False
                            self.handle_create_attribute(response, field, Message.min.value.replace("{1}", f"{rule_dict[rule]}"))
                    case "max":
                        if value < rule_dict[rule]:
                            passed = False
                            self.handle_create_attribute(response, field, Message.max.value.replace("{1}", f"{rule_dict[rule]}"))
                    case "range":
                        # Range sẽ là 1 mảng [a,b].
                        if value < rule_dict[rule][0] or value > rule_dict[rule][1]:
                            passed = False
                            self.handle_create_attribute(response, field, Message.range.value.replace("{1}", f"{rule_dict[rule][0]}").replace("{2}", f"{rule_dict[rule][1]}"))
                    case "step":
                        rule_dict[rule] = 1 if rule_dict[rule] == 0 else rule_dict[rule]
                        division_value = int(value / rule_dict[rule])
                        if float(division_value) != value / rule_dict[rule]:
                            passed = False
                            self.handle_create_attribute(response, field, Message.step.value.replace("{1}", f"{rule_dict[rule]}"))
                    case "email":
                        if not re.match(r"^[\w\-\.]+@([\w\-]+\.)+[\w\-]{2,4}$", str(value)):
                            passed = False
                            self.handle_create_attribute(response, field, Message.email.value)
                    case "date":
                        try:
                            datetime.strptime(value, "%Y-%m-%d")
                        except:
                            passed = False
                            self.handle_create_attribute(response, field, Message.date.value)
                    case "number":
                        try:
                            if "foreign_key" not in rule_dict.keys():
                                float(value)
                        except:
                            self.handle_create_attribute(response, field, Message.number.value)
                    case "digits":
                        if "foreign_key" not in rule_dict.keys():
                            if not value.isdigit():
                                passed = False
                                self.handle_create_attribute(response, field, Message.digits.value)
                    case "equal_to":
                        if value != rule_dict[rule]:
                            passed = False
                            self.handle_create_attribute(response, field, Message.equal_to.value)
                    case "foreign_key":
                        # Giả sử chúng ta có một hàm kiểm tra khóa ngoại.
                        # Nếu không tìm thấy bản ghi, sẽ trả về False.
                        if not self.check_foreign_key(value, rule_dict[rule]):
                            passed = False
                            self.handle_create_attribute(response, field, Message.foreign_key.value)

                    # Các case khác sẽ được thiết lập sau.
        return passed, response
