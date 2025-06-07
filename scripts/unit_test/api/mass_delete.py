from ..unit_test_message import Message


class MassDeleteGenerator:
    """
    Lớp sinh dữ liệu kiểm thử cho API mass_delete
    """

    def __init__(self, model=None):
        self.model = model
        self.test_cases = []

    def _make_case(self, request, response):
        self.test_cases.append({"request": request, "expected_response": response, "info": {"route": f"/api/{self.model}/delete", "method": "DELETE"}})

    def valid_case(self):
        self._make_case({"idlist": "{valid_idlist}"}, {"code": 200, "status": "success", "message": "Xóa bản ghi thành công"})

    def invalid_idlist_case(self):
        self._make_case({"idlist": "{invalid_idlist}"}, {"code": "D604", "status": "warning", "message": "Danh sách có chứa id không còn tồn tại.", "response": {"idlist": [Message.existence.value]}})

    def generate(self):
        self.valid_case()
        self.invalid_idlist_case()
        return self.test_cases
