from ..unit_test_message import Message


class MassCopyGenerator:
    """
    Lớp sinh dữ liệu kiểm thử cho API mass_copy
    """

    def __init__(self, model=None):
        self.test_cases = []
        self.model = model

    def _make_case(self, request, response):
        self.test_cases.append({"request": request, "expected_response": response, "info": {"route": f"/api/{self.model}/copy", "method": "POST"}})

    def valid_case(self):
        request = {"idlist": "{valid_idlist}"}
        response = {"code": 200, "status": "success", "message": "Sao chép bản ghi thành công"}
        self._make_case(request, response)

    def invalid_idlist_case(self):
        request = {"idlist": "{invalid_idlist}"}
        response = {"code": "D604", "status": "warning", "message": "Danh sách có chứa id không còn tồn tại."}
        self._make_case(request, response)

    def generate(self):
        self.valid_case()
        self.invalid_idlist_case()
        return self.test_cases
