from ..unit_test_message import Message


class MassCopyGenerator:
    """
    Lớp sinh dữ liệu kiểm thử cho API mass_copy
    """

    def __init__(self):
        self.test_cases = []

    def _make_case(self, idlist, expect_code, status, message, response=None):
        request = {"idlist": idlist}
        response = response or {}
        self.test_cases.append({"request": request, "response": response, "status": status, "code": expect_code, "message": message})

    def valid_case(self):
        self._make_case(idlist="{valid_idlist}", expect_code=200, status="success", message="Sao chép bản ghi thành công")

    def invalid_idlist_case(self):
        self._make_case(idlist="{invalid_idlist}", expect_code="D604", status="warning", message="Danh sách có chứa id không còn tồn tại.", response={"idlist": [Message.existence.value]})

    def generate(self):
        self.valid_case()
        self.invalid_idlist_case()
        return self.test_cases
