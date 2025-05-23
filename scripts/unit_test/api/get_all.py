import random
from ..unit_test_utils import UnitTestUtils
from ..unit_test_message import Message


class GetAllGenerator:
    """
    Lớp sinh dữ liệu kiểm thử cho API get_all
    """

    def __init__(self, column_list):
        self.column_list = column_list
        self.request_list = []
        self.response_list = []

    def valid_case(self, num_col=1):
        cols = random.sample(self.column_list, k=random.randint(max(1, num_col), len(self.column_list)))
        self.request_list.append({"columnlist": ",".join(cols)})
        self.response_list.append({"code": 200, "status": "success"})

    def invalid_case(self, num_col=1):
        max_length = max(len(col) for col in self.column_list)
        fake_cols = [UnitTestUtils.generate_string_between(max_length + 1, max_length + 5) for _ in self.column_list]
        cols = random.sample(fake_cols, k=random.randint(max(1, num_col), len(fake_cols)))
        self.request_list.append({"columnlist": ",".join(cols)})
        self.response_list.append({"code": "B607", "status": "error", "message": Message.columnlist.value})

    def generate(self):
        mid = max(1, int(len(self.column_list) / 2))
        self.valid_case(1)
        self.valid_case(mid)
        self.valid_case(len(self.column_list))
        self.invalid_case(1)
        self.invalid_case(mid)
        self.invalid_case(len(self.column_list))
        return self.request_list, self.response_list
