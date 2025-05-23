from enum import Enum
import random
from datetime import datetime
import string


class CharacterType(Enum):
    LITERAL = r"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    NUMERIC = r"0123456789"
    NORMAL = LITERAL + NUMERIC
    SPECIAL = r"!\'#$%&'()*+,-./:;<=>?@[]^_`{|}~€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ¡¢£¤¥¦§¨©ª«¬­®¯±´µ¶·¸º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ"
    ALL = NORMAL + SPECIAL


class UnitTestUtils:

    @staticmethod
    def generate_string_between(num_min: int = 0, num_max: int = 99999, string_type: CharacterType = CharacterType.NORMAL):
        """
        Hàm tạo ra xâu ký tự với độ dài ngẫu nhiên nằm giữa khoảng bé hơn và khoảng lớn hơn.
        - Các thuộc tính:
            + num_min: Độ dài tối thiểu
            + num_max: Độ dài tối đa
            + string_type: Kiểu xâu muốn trả về, mặc định là kiểu có chữ và số
        """
        random_between_length = random.randint(num_min, num_max)
        str_return = ""
        for i in range(random_between_length):
            rand_number = random.randint(0, len(string_type) - 1)
            str_return += string_type[rand_number]
        return str_return

    @staticmethod
    def generate_string_specific(num_character: int = 10, string_type: CharacterType = CharacterType.NORMAL):
        """
        Hàm tạo ra xâu ký tự với độ dài xác định cụ thể.
        - Các thuộc tính:
            + num_character: Độ dài xác định
            + string_type: Kiểu xâu muốn trả về, mặc định là kiểu có chữ và số
        """
        str_return = ""
        for i in range(int(num_character)):
            rand_number = random.randint(0, len(string_type) - 1)
            str_return += string_type[rand_number]
        return str_return

    @staticmethod
    def generate_string_above(num_character: int = 10, string_type: CharacterType = CharacterType.NORMAL):
        """
        Hàm tạo ra xâu ký tự với độ dài ngẫu nhiên nằm trên khoảng cho trước, tối đa nằm trên khoảng 100 ký tự.
        - Các thuộc tính:
            + num_character: Độ dài xác định
            + type: Kiểu xâu muốn trả về, mặc định là kiểu có chữ và số
        """

        random_string_length = random.randint(num_character + 1, num_character + 100)
        str_return = ""
        for i in range(random_string_length):
            rand_number = random.randint(0, len(string_type) - 1)
            str_return += string_type[rand_number]
        return str_return

    @staticmethod
    def generate_string_under(num_character: int = 10, string_type: CharacterType = CharacterType.NORMAL):
        """
        Hàm tạo ra xâu ký tự với độ dài ngẫu nhiên nằm dưới khoảng cho trước.
        - Các thuộc tính:
            + num_character: Độ dài xác định
            + type: Kiểu xâu muốn trả về, mặc định là kiểu có chữ và số
        """
        str_return = ""
        random_string_length = random.randint(0, num_character)
        for i in range(random_string_length):
            rand_number = random.randint(0, len(string_type) - 1)
            str_return += string_type[rand_number]
        return str_return

    @staticmethod
    def generate_datetime():
        """
        Phương thức trả về xâu ký tự có dạng datetime
        """
        return str(datetime.now().strftime("%Y-%m-%d"))

    @staticmethod
    def generate_random_email():
        """
        Phương thức tạo ra chuỗi email thỏa mãn điều kiện của một email với
        regex: ^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$
        """

        user_chars = string.ascii_letters + string.digits + "."
        domain_chars = string.ascii_letters + string.digits + "-"

        user_length = random.randint(1, 10)
        domain_length = random.randint(1, 10)
        tld_length = random.randint(2, 4)

        user = "".join(random.choice(user_chars) for _ in range(user_length))
        domain = "".join(random.choice(domain_chars) for _ in range(domain_length))
        tld = "".join(random.choice(string.ascii_letters) for _ in range(tld_length))

        email = f"{user}@{domain}.{tld}"
        return email
