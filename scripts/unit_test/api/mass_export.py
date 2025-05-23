import random
from ..unit_test_utils import UnitTestUtils
from ..unit_test_message import Message


class MassExportGenerator:
    """
    Lớp sinh dữ liệu kiểm thử cho API mass_export
    """

    def __init__(self, column_list, config):
        self.column_list = column_list
        self.config = config  # config.TYPE_EXPORT & config.ID_LIST_CHOICE
        self.test_cases = []

    def _make_case(self, columnlist, export_type, idlist, expect_code, expect_status, expect_message=""):
        request = {"columnlist": columnlist, "type": export_type, "idlist": idlist}
        response = {"code": expect_code, "status": expect_status, "message": expect_message}
        self.test_cases.append({"request": request, "response": response})

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
        typ = random.choice(self.config.TYPE_EXPORT["valid"])
        idlist = self.config.ID_LIST_CHOICE["valid"]
        self._make_case(col, typ, idlist, 200, "success")

    def invalid_type_case(self):
        col = self._generate_valid_columnlist()
        typ = random.choice(self.config.TYPE_EXPORT["invalid"])
        idlist = self.config.ID_LIST_CHOICE["valid"]
        self._make_case(col, typ, idlist, self.config.ERROR_CODE + "601", "error", "Định dạng tệp xuất ra không đúng.")

    def invalid_columnlist_case(self):
        col, diff = self._generate_invalid_columnlist()
        typ = random.choice(self.config.TYPE_EXPORT["valid"])
        idlist = self.config.ID_LIST_CHOICE["valid"]
        self._make_case(col, typ, idlist, self.config.ERROR_CODE + "607", "error", Message.columnlist.value + f" {diff}")

    def invalid_idlist_format_case(self):
        col = self._generate_valid_columnlist()
        typ = random.choice(self.config.TYPE_EXPORT["valid"])
        idlist = self.config.ID_LIST_CHOICE["invalid_format"]
        self._make_case(col, typ, idlist, 400, "error", "Đầu vào cho tham số không đúng.")

    def invalid_idlist_existence_case(self):
        col = self._generate_valid_columnlist()
        typ = random.choice(self.config.TYPE_EXPORT["valid"])
        idlist = self.config.ID_LIST_CHOICE["invalid_existence"]
        self._make_case(col, typ, idlist, self.config.ERROR_CODE + "604", "warning", "Danh sách có chứa id không còn tồn tại.")

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
