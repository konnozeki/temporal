import random
import string
from importfile import ImportFile
from message import Message

METHOD = "get_by_page"


class GetByPageGenerator(ImportFile):
    """
    Lớp sinh dữ liệu kiểm thử cho API get_by_page
    """

    def __init__(self, xml_file_name, filePath, number_of_test=100, valid_id=1):
        ImportFile.__init__(
            self, xml_file_name, filePath, number_of_test, METHOD, valid_id
        )

    def __generate_invalid_order(self):
        return_order = self.order_alias_list[0]
        while return_order in self.order_alias_list:
            return_order = "".join(
                random.choice(string.ascii_letters + string.digits + "@#$%^&*")
                for j in range(3)
            )
        return return_order

    def generate(self):
        iteration = 0
        max_length_item = max(len(item) for item in self.column_list)
        while iteration < self.number_of_test:
            column_validation = random.choice(["valid", "invalid"])
            order_validation = random.choice(["valid", "invalid"])
            page_validation = random.choice(["valid", "invalid"])
            if page_validation == "valid":
                if order_validation == "valid":
                    if column_validation == "valid":
                        self.id_list.append(str(random.randint(1, 10)))
                        self.request_list.append(
                            {
                                "columnlist": self._generate_valid_column_list(),
                                "order": random.choice(self.order_alias_list),
                            }
                        )
                        self.response_message_list.append("")
                        self.response_code_list.append(200)
                        self.response_status_list.append("success")
                    else:
                        self.id_list.append(str(random.randint(1, 10)))
                        column_list, raw_segments = self._generate_invalid_column_list(
                            max_length_item, len(self.column_list)
                        )
                        difference = (set(raw_segments)).difference(self.column_list)
                        self.request_list.append({"columnlist": column_list})
                        self.response_message_list.append(
                            Message().DEFAULT_MESSAGE["columnlist"] + f" {difference}"
                        )
                        self.response_code_list.append(
                            self.method["error_code"] + "607"
                        )
                        self.response_status_list.append("error")
                else:
                    invalid_order = self.__generate_invalid_order()
                    self.id_list.append(str(random.randint(1, 10)))
                    self.request_list.append(
                        {
                            "columnlist": self._generate_valid_column_list(),
                            "order": invalid_order,
                        }
                    )
                    self.response_message_list.append(
                        Message()
                        .DEFAULT_MESSAGE["default"]
                        .replace("{1}", f"'{invalid_order}'")
                    )
                    self.response_code_list.append(self.method["error_code"] + "600")
                    self.response_status_list.append("error")
            else:
                self.id_list.append(random.randint(-10, -1))
                self.request_list.append(
                    {
                        "columnlist": self._generate_valid_column_list(),
                        "order": random.choice(self.order_list),
                    }
                )
                self.response_message_list.append(
                    Message().DEFAULT_MESSAGE["page_number"]
                )
                self.response_code_list.append(self.method["error_code"] + "601")
                self.response_status_list.append("error")

            self.response_data.append({})
            iteration += 1

        self._write_excel()
