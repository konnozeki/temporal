import random
from ..unit_test_utils import UnitTestUtils
from ..unit_test_message import Message


class StoreGenerator:
    """
    Lớp sinh dữ liệu kiểm thử cho API store
    """

    def __init__(self, field_list, criteria):
        self.field_list = field_list  # Danh sách tên các trường
        self.criteria = criteria  # Dict các rule cho từng trường
        self.test_cases = []

    def _make_case(self, request, response, status, code, message):
        self.test_cases.append({"request": request, "response": response, "status": status, "code": code, "message": message})

    def _generate_valid_request(self):
        request = {}

        for field in self.field_list:
            rules = self.criteria.get(field, {})

            if rules.get("email"):
                request[field] = UnitTestUtils.generate_random_email()

            elif rules.get("number"):
                request[field] = random.randint(1, 99999)

            elif rules.get("date"):
                request[field] = UnitTestUtils.generate_datetime()

            elif rules.get("foreign_key"):
                reference = rules["foreign_key"]
                request[field] = f"{{valid_{reference}_id}}"

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
            rules = self.criteria.get(field, {})
            inject_error = random.random() < 0.5 and error_injected < max_errors

            if inject_error:
                error_injected += 1
                failed_fields.append(field)

                if rules.get("email"):
                    value = "invalid_email"

                elif rules.get("number"):
                    value = "abc"

                elif rules.get("date"):
                    value = "31-02-9999"

                elif rules.get("foreign_key"):
                    reference = rules["foreign_key"]
                    value = f"{{invalid_{reference}_id}}"

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

                elif rules.get("number"):
                    value = random.randint(1, 99999)

                elif rules.get("date"):
                    value = UnitTestUtils.generate_datetime()

                elif rules.get("foreign_key"):
                    reference = rules["foreign_key"]
                    value = f"{{valid_{reference}_id}}"

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
        response = {}
        self._make_case(request, response, "success", 200, "Tạo bản ghi thành công")

    def invalid_case(self):
        request, failed_fields = self._generate_invalid_request()
        response = {field: [] for field in failed_fields}
        self._make_case(request, response, "warning", "B603", "Lỗi kiểm tra dữ liệu.")

    # --------------------------
    # Sinh toàn bộ test case
    # --------------------------

    def generate(self):
        self.valid_case()
        self.invalid_case()
        return self.test_cases
