import random
from ..unit_test_utils import UnitTestUtils
from ..unit_test_message import Message


class MassExportGenerator:
    """
    Lớp sinh dữ liệu kiểm thử cho API mass_export
    """

    def __init__(self, column_list, model=None):
        self.model = model
        self.column_list = column_list
        self.test_cases = []

        self.valid_types = ["pdf", "xlsx", "docx", "csv", "json", "xml"]
        self.invalid_types = ["exe", "html", "zip", "mp3", "unknown"]

    def _make_case(self, request, response):
        self.test_cases.append({"request": request, "expected_response": response, "info": {"route": f"/api/{self.model}/export", "method": "GET"}})

    def _generate_valid_columnlist(self):
        return ",".join(random.sample(self.column_list, k=random.randint(1, len(self.column_list))))

    def _generate_invalid_columnlist(self):
        max_length = max(len(col) for col in self.column_list)
        invalid = [UnitTestUtils.generate_string_between(max_length + 1, max_length + 5) for _ in range(3)]
        return ",".join(invalid), set(invalid)

    # --------------------------
    # Các chiến lược test case
    # --------------------------

    def valid_case(self):
        col = self._generate_valid_columnlist()
        typ = random.choice(self.valid_types)
        self._make_case({"columnlist": col, "type": typ, "idlist": "{valid_idlist}"}, {"code": 200, "status": "success"})

    def invalid_type_case(self):
        col = self._generate_valid_columnlist()
        typ = random.choice(self.invalid_types)
        self._make_case({"columnlist": col, "type": typ, "idlist": "{valid_idlist}"}, {"code": "I601", "status": "error", "message": "Định dạng tệp xuất ra không đúng."})

    def invalid_columnlist_case(self):
        col, diff = self._generate_invalid_columnlist()
        typ = random.choice(self.valid_types)
        self._make_case({"columnlist": col, "type": typ, "idlist": "{valid_idlist}"}, {"code": "I607", "status": "error", "message": Message.columnlist.value + f" {diff}"})

    def invalid_idlist_format_case(self):
        col = self._generate_valid_columnlist()
        typ = random.choice(self.valid_types)
        self._make_case({"columnlist": col, "type": typ, "idlist": "{invalid_format_idlist}"}, {"code": 400, "status": "error", "message": "Đầu vào cho tham số không đúng."})

    def invalid_idlist_existence_case(self):
        col = self._generate_valid_columnlist()
        typ = random.choice(self.valid_types)
        self._make_case({"columnlist": col, "type": typ, "idlist": "{invalid_existence_idlist}"}, {"code": "I604", "status": "warning", "message": "Danh sách có chứa id không còn tồn tại."})

    # --------------------------
    # Sinh toàn bộ test case
    # --------------------------

    def generate(self):
        self.valid_case()
        self.invalid_type_case()
        self.invalid_columnlist_case()
        self.invalid_idlist_format_case()
        self.invalid_idlist_existence_case()
        return self.test_cases
