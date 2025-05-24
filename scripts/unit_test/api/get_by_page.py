import random
import string
from ..unit_test_utils import UnitTestUtils
from ..unit_test_message import Message


class GetByPageGenerator:
    """
    Lớp sinh dữ liệu kiểm thử cho API get_by_page
    Dựa vào các tham số: page, size, order, search, columnlist
    """

    def __init__(self, column_list, order_alias_list):
        self.column_list = column_list
        self.order_alias_list = order_alias_list
        self.test_cases = []

    def _make_case(self, request, response):
        self.test_cases.append({"request": request, "response": response})

    def _generate_invalid_order(self):
        while True:
            order = "".join(random.choices(string.ascii_letters + string.digits + "@#$%^&*", k=3))
            if order not in self.order_alias_list:
                return order

    def _generate_valid_columnlist(self, num_col=None):
        if not num_col:
            num_col = random.randint(1, len(self.column_list))
        return ",".join(random.sample(self.column_list, k=num_col))

    def _generate_invalid_columnlist(self):
        max_length = max(len(col) for col in self.column_list)
        return ",".join([UnitTestUtils.generate_string_between(max_length + 1, max_length + 5) for _ in range(3)])

    # --------------------------
    # Các chiến lược test case
    # --------------------------

    def valid_case(self):
        request = {"page": 1, "size": 10, "order": random.choice(self.order_alias_list), "search": "", "columnlist": self._generate_valid_columnlist()}
        response = {"code": 200, "status": "success"}
        self._make_case(request, response)

    def invalid_page_case(self):
        request = {"page": -1, "size": 10, "order": random.choice(self.order_alias_list), "search": "", "columnlist": self._generate_valid_columnlist()}
        response = {"code": "B601", "status": "error", "message": Message.page_number.value}
        self._make_case(request, response)

    def invalid_order_case(self):
        invalid_order = self._generate_invalid_order()
        request = {"page": 1, "size": 10, "order": invalid_order, "search": "", "columnlist": self._generate_valid_columnlist()}
        response = {"code": "B600", "status": "error", "message": Message.default.value.replace("{1}", f"'{invalid_order}'")}
        self._make_case(request, response)

    def invalid_columnlist_case(self):
        request = {"page": 1, "size": 10, "order": random.choice(self.order_alias_list), "search": "", "columnlist": self._generate_invalid_columnlist()}
        response = {"code": "B607", "status": "error", "message": Message.columnlist.value}
        self._make_case(request, response)

    # --------------------------
    # Sinh tất cả test case
    # --------------------------

    def generate(self):
        self.valid_case()
        self.invalid_page_case()
        self.invalid_order_case()
        self.invalid_columnlist_case()
        return self.test_cases
