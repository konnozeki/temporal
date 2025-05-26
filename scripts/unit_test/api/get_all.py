import random
from ..unit_test_utils import UnitTestUtils
from ..unit_test_message import Message


class GetAllGenerator:
    """
    Lớp sinh dữ liệu kiểm thử cho API get_all
    """

    def __init__(self, column_list):
        self.column_list = column_list
        self.test_cases = []

    def _make_case(self, request, response):
        self.test_cases.append({"request": request, "response": response})

    def valid_case(self, num_col=1):
        cols = random.sample(self.column_list, k=random.randint(max(1, num_col), len(self.column_list)))
        request = {"columnlist": ",".join(cols)}
        response = {"code": 200, "status": "success"}
        self._make_case(request, response)

    def invalid_case(self, num_col=1):
        max_length = max(len(col) for col in self.column_list)
        fake_cols = [UnitTestUtils.generate_string_between(max_length + 1, max_length + 5) for _ in self.column_list]
        cols = random.sample(fake_cols, k=random.randint(max(1, num_col), len(fake_cols)))
        request = {"columnlist": ",".join(cols)}
        response = {"code": "B607", "status": "error", "message": Message.columnlist.value}
        self._make_case(request, response)

    def generate(self):
        mid = max(1, int(len(self.column_list) / 2))
        self.valid_case(1)
        self.valid_case(mid)
        self.valid_case(len(self.column_list))

        self.invalid_case(1)
        self.invalid_case(mid)
        self.invalid_case(len(self.column_list))

        return self.test_cases
