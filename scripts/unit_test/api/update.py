import random
from ..unit_test_utils import UnitTestUtils
from ..unit_test_message import Message
from ..unit_test_validator import Validator


class UpdateGenerator:
    """
    Lớp sinh dữ liệu kiểm thử cho API update
    """

    def __init__(self, field_list, criteria, model=None):
        self.model = model  # Mô hình liên quan, nếu có
        self.criteria = criteria
        self.field_list = field_list
        self.test_cases = []

    def validate(self, request):
        return Validator().validate(self.field_list, request, self.criteria)

    def _make_case(self, request, response):
        request_id = request.get("id", "{valid_id}")
        del request["id"]  # Xoá id khỏi request để tránh lặp lại trong test case
        self.test_cases.append({"request": request, "expected_response": response, "info": {"route": f"/api/{self.model}/{request_id}", "method": "PUT"}})

    def _generate_valid_request(self):
        request = {"id": "{valid_id}"}

        for field in self.field_list:
            if field == "id":
                continue
            rules = self.criteria.get(field, {})

            if rules.get("email"):
                request[field] = UnitTestUtils.generate_random_email()

            elif rules.get("foreign_key"):
                reference = rules["foreign_key"]
                request[field] = f"{{valid_{reference}_id}}"

            elif rules.get("number"):
                request[field] = random.randint(1, 99999)

            elif rules.get("date"):
                request[field] = UnitTestUtils.generate_datetime()

            elif rules.get("boolean"):
                request[field] = random.choice([True, False])

            else:
                min_len = rules.get("min_length", 1)
                max_len = rules.get("max_length", 10)
                request[field] = UnitTestUtils.generate_string_between(min_len, max_len)

        return request

    def _generate_invalid_request(self):
        request = {}
        failed_fields = []
        error_injected = 0
        max_errors = max(1, int(len(self.field_list) / 2))  # Inject khoảng 50%

        for field in self.field_list:
            if field == "id":
                continue
            rules = self.criteria.get(field, {})
            inject_error = random.random() < 0.5 and error_injected < max_errors

            if inject_error:
                error_injected += 1
                failed_fields.append(field)

                if rules.get("email"):
                    value = UnitTestUtils.generate_string_specific(10)

                elif rules.get("foreign_key"):
                    reference = rules["foreign_key"]
                    value = f"{{invalid_{reference}_id}}"

                elif rules.get("number"):
                    value = UnitTestUtils.generate_string_specific(5)

                elif rules.get("date"):
                    value = UnitTestUtils.generate_string_specific()

                elif rules.get("boolean"):
                    value = "not_a_boolean"

                elif "max_length" in rules:
                    value = UnitTestUtils.generate_string_above(rules["max_length"])

                elif rules.get("required"):
                    value = ""

                else:
                    value = None

            else:
                # fallback giá trị hợp lệ
                if rules.get("email"):
                    value = UnitTestUtils.generate_random_email()

                elif rules.get("foreign_key"):
                    reference = rules["foreign_key"]
                    value = f"{{valid_{reference}_id}}"

                elif rules.get("number"):
                    value = random.randint(1, 99999)

                elif rules.get("date"):
                    value = UnitTestUtils.generate_datetime()

                elif rules.get("boolean"):
                    value = random.choice([True, False])

                else:
                    min_len = rules.get("min_length", 1)
                    max_len = rules.get("max_length", 10)
                    value = UnitTestUtils.generate_string_between(min_len, max_len)

            request[field] = value

        return request, failed_fields

    # --------------------------
    # Chiến lược test case
    # --------------------------

    def valid_case(self):
        request = self._generate_valid_request()
        request["id"] = "{valid_id}"
        response = {
            "code": 200,
            "message": "Cập nhật dữ liệu thành công",
            "status": "success",
        }
        self._make_case(request, response)

    def invalid_case(self):
        request, failed_fields = self._generate_invalid_request()
        request["id"] = "{valid_id}"
        passed, validate_response = self.validate(request)
        response = {
            "code": "F603",
            "message": "Lỗi kiểm tra dữ liệu.",
            "status": "warning",
            "data": {"oldData": request, "errors": validate_response},
        }
        self._make_case(request, response)

    def invalid_id_case(self):
        request = self._generate_valid_request()
        request["id"] = "{invalid_id}"
        response = {
            "message": Message.existence.value,
            "code": "F604",
            "status": "error",
        }
        self._make_case(request, response)

    # --------------------------
    # Sinh toàn bộ test case
    # --------------------------

    def generate(self):
        self.valid_case()
        self.valid_case()
        self.valid_case()
        self.invalid_case()
        self.invalid_case()
        self.invalid_case()
        self.invalid_case()
        self.invalid_case()
        self.invalid_case()
        self.invalid_case()
        self.invalid_case()
        self.invalid_id_case()
        self.invalid_id_case()
        self.invalid_id_case()
        self.invalid_id_case()
        self.invalid_id_case()
        self.invalid_id_case()
        return self.test_cases
