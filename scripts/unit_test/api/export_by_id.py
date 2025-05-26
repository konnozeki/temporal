import random
from ..unit_test_utils import UnitTestUtils
from ..unit_test_message import Message


class ExportByIDGenerator:
    """
    Lớp sinh dữ liệu kiểm thử cho API export_by_id
    """

    def __init__(self, column_list):
        self.column_list = column_list
        self.type_export_config = {"valid": ["csv", "json", "xlsx"], "invalid": ["exe", "html", "zip", "mp3", "unknown"]}

        self.test_cases = []

    def _make_case(self, id_placeholder, columnlist, export_type, expect_code, expect_status, expect_message=""):
        request = {"id": id_placeholder, "columnlist": columnlist, "type": export_type}
        response = {"code": expect_code, "status": expect_status}
        if expect_message:
            response["message"] = expect_message

        self.test_cases.append({"request": request, "response": response})

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
        self._make_case("{valid_id}", col, typ, 200, "success")

    def invalid_id_case(self):
        col = self._generate_valid_columnlist()
        typ = random.choice(self.type_export_config["valid"])
        self._make_case("{invalid_id}", col, typ, "D604", "error", "Mã bản ghi không tồn tại trong bảng dữ liệu.")

    def invalid_type_case(self):
        col = self._generate_valid_columnlist()
        typ = random.choice(self.type_export_config["invalid"])
        self._make_case("{valid_id}", col, typ, "D601", "error", "Định dạng tệp muốn xuất ra không đúng.")

    def invalid_columnlist_case(self):
        col, diff = self._generate_invalid_columnlist()
        typ = random.choice(self.type_export_config["valid"])
        self._make_case("{valid_id}", col, typ, "D607", "error", Message.columnlist.value + f" {diff}")

    # --------------------------
    # Sinh tất cả test case
    # --------------------------

    def generate(self):
        self.valid_case()
        self.invalid_id_case()
        self.invalid_type_case()
        self.invalid_columnlist_case()
        return self.test_cases
