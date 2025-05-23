import random
from ..unit_test_utils import UnitTestUtils
from ..unit_test_message import Message


class StoreGenerator:
    """
    Lớp sinh dữ liệu kiểm thử cho API store
    """

    def __init__(self, field_list):
        self.field_list = field_list  # Tên các trường cần kiểm tra
        self.test_cases = []

    def _make_case(self, request, response, status, code, message):
        self.test_cases.append({"request": request, "response": response, "status": status, "code": code, "message": message})

    def _generate_valid_request(self):
        pass

    def _generate_invalid_request(self):
        pass

    # --------------------------
    # Chiến lược test case
    # --------------------------

    def valid_case(self):
        request = self._generate_valid_request()
        response = {}
        self._make_case(request, response, "success", 200, "Tạo bản ghi thành công")

    def invalid_case(self):
        request, failed_fields = self._generate_invalid_request()
        response = {field: [Message.default_field_error.value] for field in failed_fields}
        self._make_case(request, response, "warning", "B603", "Lỗi kiểm tra dữ liệu.")

    # --------------------------
    # Sinh test case
    # --------------------------

    def generate(self):
        self.valid_case()
        self.invalid_case()
        return self.test_cases
