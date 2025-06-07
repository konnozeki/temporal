import random
from ..unit_test_utils import UnitTestUtils
from ..unit_test_message import Message


class ExportByIDGenerator:
    """
    Lớp sinh dữ liệu kiểm thử cho API export_by_id
    """

    def __init__(self, column_list, model=None):
        self.model = model
        self.column_list = column_list
        self.type_export_config = {"valid": ["csv", "json", "xlsx"], "invalid": ["exe", "html", "zip", "mp3", "unknown"]}

        self.test_cases = []

    def _make_case(self, request, response):
        self.test_cases.append({"request": request, "expected_response": response, "info": {"route": f"/api/{self.model}/export/{request['id']}", "method": "GET"}})

    def _generate_valid_columnlist(self):
        return ",".join(random.sample(self.column_list, k=random.randint(1, len(self.column_list))))

    def _generate_invalid_columnlist(self):
        max_length = max(len(col) for col in self.column_list)
        invalid = [UnitTestUtils.generate_string_between(max_length + 1, max_length + 5) for _ in range(3)]
        return ",".join(invalid), set(invalid)

    # --------------------------
    # Chiến lược sinh test case
    # --------------------------

    def valid_case(self):
        col = self._generate_valid_columnlist()
        typ = random.choice(self.type_export_config["valid"])
        request = {"id": "{valid_id}", "columnlist": col, "type": typ}
        response = {"code": 200, "status": "success"}
        self._make_case(request, response)

    def invalid_id_case(self):
        col = self._generate_valid_columnlist()
        typ = random.choice(self.type_export_config["valid"])
        request = {"id": "{invalid_id}", "columnlist": col, "type": typ}
        response = {"code": "D604", "status": "error", "message": "Mã bản ghi không tồn tại trong bảng dữ liệu."}
        self._make_case(request, response)

    def invalid_type_case(self):
        col = self._generate_valid_columnlist()
        typ = random.choice(self.type_export_config["invalid"])
        request = {"id": "{valid_id}", "columnlist": col, "type": typ}
        response = {"code": "D601", "status": "error", "message": "Định dạng tệp muốn xuất ra không đúng."}
        self._make_case(request, response)

    def invalid_columnlist_case(self):
        col, diff = self._generate_invalid_columnlist()
        request = {"id": "{valid_id}", "columnlist": col, "type": random.choice(self.type_export_config["valid"])}
        response = {"code": "D607", "status": "error", "message": Message.columnlist.value + f" {diff}"}
        self._make_case(request, response)

    # --------------------------
    # Sinh tất cả test case
    # --------------------------

    def generate(self):
        self.valid_case()
        self.invalid_id_case()
        self.invalid_type_case()
        self.invalid_columnlist_case()
        return self.test_cases
