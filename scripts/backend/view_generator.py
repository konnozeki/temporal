import psycopg2


class ViewGenerator:
    """
    Lớp `ViewGenerator` chịu trách nhiệm sinh ra mã định nghĩa `View Model` trong Odoo để hỗ trợ việc kiểm tra liên kết dữ liệu giữa các bảng thông qua các foreign key.

    ### Mục đích tổng thể:
    - Tự động hóa việc tạo ra các view Odoo không thực thi (_auto = False) nhằm thống kê số lượng liên kết từ các bảng khác tới bảng hiện tại.
    - Hỗ trợ cơ chế `can_delete` để xác định bản ghi có đang được sử dụng ở nơi khác hay không.
    - Tránh lỗi logic khi xóa dữ liệu hoặc khi cần kiểm tra sự tồn tại của các liên kết phụ thuộc trong hệ thống backend.

    ---
    ### Thuộc tính:
    - `xml_dict` (`dict`): Dữ liệu cấu hình XML đầu vào, bao gồm định nghĩa tên model và các thông tin metadata.
    - `db_name` (`str`): Tên database để kết nối (mặc định là `"nagaco"`).
    - `db_user` (`str`): Tên người dùng PostgreSQL (mặc định là `"odoo"`).
    - `db_password` (`str`): Mật khẩu cho kết nối CSDL.
    - `db_host` (`str`): Địa chỉ máy chủ CSDL.
    - `db_port` (`int`): Cổng kết nối CSDL.
    - `model_name` (`str`): Tên model chính (từ XML).
    - `class_name` (`str`): Tên class Python hóa từ `model_name`.
    - `object_name` (`str`): Tên rút gọn không có tiền tố `nagaco_`, dùng trong định danh field.
    - `number_type` (`List[str]`): Các kiểu dữ liệu được xem là kiểu số.

    ---
    ### Phương thức chính:

    #### `create_view(self, records)`
    - Sinh class `View` có các trường đếm liên kết (`count(*)`) từ các bảng khác.
    - Mỗi bảng liên kết sẽ sinh một trường `fields.Integer`.
    - Dùng khi model có ít nhất một bảng liên kết foreign key.

    #### `create_view_empty(self, records)`
    - Sinh class `View` rỗng chỉ chứa khóa chính (Many2one).
    - Dùng khi không có bảng nào liên kết tới model hiện tại.

    #### `generate_view(self)`
    - Kết nối PostgreSQL để truy vấn `information_schema` tìm các bảng liên kết tới model hiện tại.
    - Dựa vào kết quả, sinh ra nội dung Python tương ứng bằng cách gọi `create_view()` hoặc `create_view_empty()`.
    """

    def __init__(self, xml_dict):
        self.xml_dict = xml_dict
        self.db_name = "nagaco"
        self.db_user = "odoo"
        self.db_password = "odoo17@2023"
        self.db_host = "192.168.1.8"
        self.db_port = 5433
        self.model_name = self.xml_dict["root"]["model"]
        self.class_name = self.model_name.replace("_", " ").title().replace(" ", "_")
        self.object_name = self.model_name.replace("nagaco_", "")
        self.number_type = ["int", "smallint", "float", "double", "bool"]

    def create_view(self, records):
        """
        Phương thức `create_view` sinh ra mã Python định nghĩa một class view Odoo để phục vụ kiểm tra dữ liệu liên kết (foreign key) trong hệ thống.

        ### Mục đích:
        - Tạo một `View Model` không sinh bảng thật trong database, dùng để tổng hợp số lượng bản ghi liên kết tới từng dòng trong bảng chính.
        - Mỗi trường được tạo là một `fields.Integer` hiển thị số lượng bản ghi có liên kết khóa ngoại tới dòng tương ứng.

        ### Đầu vào:
        - `records` (List[Tuple[str, str]]): Danh sách gồm `(table_name, column_name)` thể hiện bảng liên kết và cột khóa ngoại.

        ### Cách hoạt động:
        - Với mỗi bảng liên kết `cl` và cột `fi`, sinh ra:
            + Một trường `fields.Integer` đếm số bản ghi (`count(*)`) liên kết tới `id` của bảng chính.
            + Tên trường có dạng `<fk_alias>_<i>_count`.
        - Sinh view SQL tương ứng với câu lệnh `SELECT ... FROM <main_table> source`.

        ### Đầu ra:
        - Trả về chuỗi mã định nghĩa class view, có thể ghi vào file Python (thường là `models/view.py`).

        ### Ghi chú:
        - View này dùng để hỗ trợ logic `can_delete`, kiểm tra xem bản ghi có đang được tham chiếu ở nơi khác không.
        """
        fk_name = [(r[0].replace("nagaco_", ""), r[0], r[1]) for r in records]
        fields = "\n".join([f"""\t{fk}_{i}_count = fields.Integer(string='Count of {cl}', readonly=True)""" for (i, (fk, cl, fi)) in enumerate(fk_name)])
        coalesces = ",\n".join([f"""\t\t\t\t(select count(*) from {cl} where {cl}.{fi} = source.id) AS {fk}_{i}_count""" for (i, (fk, cl, fi)) in enumerate(fk_name)])
        str = f"""
class {self.class_name}_View(models.Model):
	_name = '{self.model_name}_view'
	_auto = False  # Không tạo bảng mới trong CSDL
	_description = 'Table {self.model_name} View'
	{self.object_name}_id = fields.Many2one('{self.model_name}', string='{self.object_name}', readonly=True)
{fields}

	def init(self):
		self.env.cr.execute(\"\"\"
			CREATE OR REPLACE VIEW {self.model_name}_view AS
			SELECT
				source.id AS {self.object_name}_id,
{coalesces}
			FROM
				{self.model_name} source
	\"\"\")
"""
        return str

    def create_view_empty(self, records):
        """
        Phương thức `create_view_empty` tạo một class view Odoo đơn giản khi không có liên kết khóa ngoại nào.

        ### Mục đích:
        - Đảm bảo hệ thống luôn có view tương ứng cho mỗi model, kể cả khi không có bảng nào tham chiếu tới model đó.
        - Tránh lỗi khi thực thi các logic phụ thuộc vào view (như `can_delete`) nếu không có liên kết.

        ### Đầu vào:
        - `records` (List[Any]): Dữ liệu truy vấn (không sử dụng bên trong hàm này, chỉ để giữ giao diện nhất quán với `create_view`).

        ### Cách hoạt động:
        - Tạo một view chỉ chứa duy nhất trường `model_id` (Many2one trỏ về model chính).
        - Câu lệnh SQL `CREATE OR REPLACE VIEW` chỉ đơn giản ánh xạ `id` → `{model_name}_id`.

        ### Đầu ra:
        - Trả về chuỗi mã Python định nghĩa một view rỗng (chỉ có khóa chính), đủ để hệ thống xử lý mà không lỗi.

        """
        str = f"""
class {self.class_name}_View(models.Model):
	_name = '{self.model_name}_view'
	_auto = False  # Không tạo bảng mới trong CSDL
	_description = 'Table {self.model_name} View'
	{self.object_name}_id = fields.Many2one('{self.model_name}', string='{self.object_name}', readonly=True)

	def init(self):
		self.env.cr.execute(\"\"\"
			CREATE OR REPLACE VIEW {self.model_name}_view AS
			SELECT
				source.id AS {self.object_name}_id
			FROM
				{self.model_name} source
	\"\"\")
"""

        return str

    def generate_view(self):
        """
        Phương thức `generate_view` kết nối đến database để tìm các bảng nào đang liên kết tới bảng hiện tại, và sinh mã định nghĩa view tương ứng.

        ### Mục đích:
        - Phát hiện các liên kết foreign key tới bảng chính thông qua truy vấn `information_schema` của PostgreSQL.
        - Tự động sinh view phù hợp (đầy đủ hoặc rỗng) dựa trên kết quả.
        - Chuẩn bị dữ liệu để hỗ trợ các logic kiểm tra liên kết như `can_delete`.

        ### Cách hoạt động:
        - Dùng psycopg2 kết nối tới database và thực hiện câu SQL truy vấn các constraint liên kết tới bảng hiện tại (`self.model_name`).
        - Nếu có kết quả:
            + Gọi `create_view(records)` để sinh mã Python định nghĩa view có trường `count`.
        - Nếu không có liên kết:
            + Gọi `create_view_empty(records)` để sinh view rỗng.

        ### Đầu ra:
        - Trả về chuỗi mã Python định nghĩa view model, bao gồm cả phần import (`from odoo import models, fields`).

        ### Ghi chú:
        - Cần các thuộc tính lớp:
            + `self.db_name`, `self.db_user`, `self.db_password`, `self.db_host`, `self.db_port`: Thông tin kết nối CSDL.
            + `self.model_name`: Tên bảng chính cần kiểm tra.
            + `self.class_name`, `self.object_name`: Dùng để đặt tên class và field view.
        - Phương thức này thường được gọi từ `generate_model.py` hoặc script sinh mã backend.

        """
        connection = psycopg2.connect(database=self.db_name, user=self.db_user, password=self.db_password, host=self.db_host, port=self.db_port)
        cursor = connection.cursor()
        sql_context = f"""
SELECT
    DISTINCT r.table_name as table_name, r.column_name as column_name
FROM information_schema.constraint_column_usage       u
INNER JOIN information_schema.referential_constraints fk
           ON u.constraint_catalog = fk.unique_constraint_catalog
               AND u.constraint_schema = fk.unique_constraint_schema
               AND u.constraint_name = fk.unique_constraint_name
INNER JOIN information_schema.key_column_usage        r
           ON r.constraint_catalog = fk.constraint_catalog
               AND r.constraint_schema = fk.constraint_schema
               AND r.constraint_name = fk.constraint_name
WHERE
    u.column_name = 'id' AND
    u.table_catalog = 'nagaco' AND
    u.table_schema = 'public' AND
    u.table_name = '{self.model_name}';
        """

        cursor.execute(sql_context)
        records = cursor.fetchall()
        return_str = ""
        if len(records) > 0:
            return_str = f"""
from enum import Enum
from odoo import models, fields

{self.create_view(records)}
"""
        else:
            return_str = f"""
from enum import Enum
from odoo import models, fields

{self.create_view_empty(records)}
"""
        return return_str
