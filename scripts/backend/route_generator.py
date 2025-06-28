from config import *
import re


class RouteGenerator:
    """
    Lớp này dùng để sinh ra cấu trúc các routes trong tệp route.py cho controller của module.
    - Các thuộc tính:
        + xml_dict: Chứa thông tin về cấu trúc của bảng
        + model_name: Tên của bảng trong CSDL
    - Các phương thức:
        + generate_route(): Sinh ra tệp route của model
    """

    def __init__(self, xml_dict):
        try:
            self.xml_dict = xml_dict["root"]["fields"]
            self.model_name = xml_dict["root"]["model"]
            self.class_name = self.model_name.replace("_", " ").title().replace(" ", "_")
            self.sub_system_code = xml_dict["root"]["sub_system_code"]
            self.module_code = xml_dict["root"]["module_code"]

            # Lấy danh sách các bảng khóa ngoại
            fk_list = []
            fk_name_list = []
            for field in xml_dict["root"]["fields"]["field"]:
                if field is None:
                    continue
                if "foreign_key" in field and field["foreign_key"] and len(field["foreign_key"].strip()) > 0:
                    fk_items = field["foreign_key"].strip().replace(" ", "").split(",")
                    fk_name = field["name"]
                    if fk_items[0]:
                        fk_list.append(re.sub("^nagaco_|^hrm_|^fin_", "", fk_items[0]))
                        fk_name_list.append(fk_name)
            self.foreign_keys = fk_list
            self.foreign_key_name = list(set(fk_name_list))

        except Exception as e:
            print(e)
            print("Định dạng tệp xml chưa đúng")
            return None

    def generate_foreign_route(self):
        """
        Phương thức `generate_foreign_route` dùng để sinh ra các route API trong Odoo cho việc truy vấn bản ghi theo trường khóa ngoại.

        ### Mục đích:
        - Tự động sinh các API dạng `/api/<model>/<foreign>` để lấy danh sách bản ghi theo từng khóa ngoại.
        - Hỗ trợ kiểm tra phân quyền nếu sử dụng `AUTH_MODE`.
        - Giảm lặp lại trong việc viết controller thủ công với mỗi trường khóa ngoại.

        ### Đầu vào:
        - Sử dụng thuộc tính `self.foreign_key_name` (List[str]) để lấy danh sách tên các trường khóa ngoại có dạng `<tên>_id`.
        - Cần các thuộc tính lớp:
            + `self.model_name` (str): Tên model kỹ thuật (ví dụ: `product_template`).
            + `self.AUTH_MODE` (bool): Có bật xác thực hay không.
            + `self.ACTION_CODE` (str): Mã hành động dùng để phân quyền (`Authentication.verify`).
            + `self.ctrl`: Controller instance xử lý logic backend (phải có method `get_all_by(...)`).
            + `me.sitemap`, `me.cors`, `me.csrf`: Các thiết lập route mặc định (gắn từ lớp ngoài vào).

        ### Cách hoạt động:
        - Với mỗi trường khóa ngoại, tạo một route như sau:
            `/api/<model>/<foreign>` (ví dụ: `/api/product/category`)
        - Trong body:
            + Nếu bật `AUTH_MODE`, gọi `Authentication.verify` để kiểm tra quyền R (read) và A (approval).
            + Tùy theo kết quả phân quyền, gọi `self.ctrl.get_all_by(...)` với các tham số phù hợp (truyền thêm `approval=True` nếu có quyền duyệt).
            + Nếu không bật xác thực → gọi controller trực tiếp không kèm `user` hay `approval`.

        ### Đầu ra:
        - Trả về chuỗi định nghĩa các route `@http.route(...)`, có thể ghi trực tiếp vào file controller của Odoo.

        ### Ghi chú:
        - Phương thức này **không kiểm tra hợp lệ khóa ngoại** – cần đảm bảo `self.foreign_key_name` được xây dựng đúng từ metadata trước đó.
        - Các route sinh ra có kiểu `http`, không dùng `json` → phù hợp cho API public hoặc GET đơn giản.
        - Tên phương thức luôn ở dạng `get_all_by_<field>`.
        """
        route_str = ""
        for fk_name in self.foreign_key_name:
            route_str += f"""
    @http.route(['/api/{self.model_name}/{fk_name.replace("_id", "")}'], type='http', auth="none", methods=['GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def get_all_by_{fk_name}(self, **kw):
        return self.base_route.get_all_by('{fk_name.replace("_id", "")}', '{fk_name}', **kw)
"""
        return route_str

    def generate_route(self):
        """
        Phương thức này cho phép tạo các route cho controller theo các thông tin trong self.xmlDict và self.model_name.
        - Các tham số: Không có
        - Các kết quả trả về:
            + Nếu tạo hệ thống các routes thành công thì thông báo thành công.
            + Ngược lại thì thông báo lỗi.
        - Các tình huống:
            1. Nếu tệp route.py đã có rồi thì báo lỗi và dừng
            2. Nếu xảy ra lỗi bất kỳ thì phải bắt được và đưa ra thông báo đã gặp lỗi
            3. Nếu tạo thành công tất cả các routes thì thông báo thành công
        """
        str_route = f"""
from odoo import http
from ..config import config as me
from ..controllers.{self.model_name}_controller import {self.class_name}_API
from ..middleware.authentication import Authentication
from .base_class.nagaco_route import Nagaco_Route


class {self.class_name}_Router(http.Controller):
    def __init__(self):
        self.base_route = Nagaco_Route(me.SYS_CODE, "{self.sub_system_code}", "{self.module_code}", {self.class_name}_API())

    @http.route(['/api/{self.model_name}'], type='http', auth="none", methods=['GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def get_all(self, **kw):
        return self.base_route.get_all(**kw)

    @http.route(['/api/{self.model_name}/page/<int:page>/'], type='http', auth="none", methods=['GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def get_by_page(self, page, **kw):
        return self.base_route.get_by_page(page, **kw)

    @http.route(['/api/{self.model_name}/<int:id>'], type='http', auth="none", methods=['GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def get_by_id(self, id, **kw):
        return self.base_route.get_by_id(id, **kw)

    @http.route(['/api/{self.model_name}'], type='http', auth="none", methods=['POST'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def store(self, **kw):
        return self.base_route.store(**kw)

    @http.route(['/api/{self.model_name}/<int:id>'], type='http', auth="none", methods=['POST', 'PUT'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def update(self, id, **kw):
        return self.base_route.update(id, **kw)

    @http.route(['/api/{self.model_name}/<int:id>'], type='http', auth="none", methods=['DELETE'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def destroy(self, id, **kw):
        return self.base_route.destroy(id, **kw)

    @http.route(['/api/{self.model_name}/copy'], type='http', auth="none", methods=['POST'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def mass_copy(self, **kw):
        return self.base_route.mass_copy(**kw)

    @http.route(['/api/{self.model_name}/delete'], type='http', auth="none", methods=['DELETE'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def mass_delete(self, **kw):
        return self.base_route.mass_delete(**kw)

    @http.route(['/api/{self.model_name}/import'], type='http', auth="none", methods=['POST'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def import_data(self, **kw):
        return self.base_route.import_data(**kw)

    @http.route(['/api/{self.model_name}/import'], type='http', auth="none", methods=['GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def get_template_import(self, **kw):
        return self.base_route.get_template_import(**kw)

    @http.route(['/api/{self.model_name}/export/<int:id>'], type='http', auth="none", methods=['POST', 'GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def export_by_id(self, id, **kw):
        return self.base_route.export_by_id(id, **kw)

    @http.route(['/api/{self.model_name}/export'], type='http', auth="none", methods=['POST', 'GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def mass_export(self, **kw):
        return self.base_route.mass_export(**kw)

    @http.route(['/api/{self.model_name}/help'], type='http', auth="none", methods=['GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def help(self, **kw):
        return self.base_route.help(**kw)

    @http.route(['/api/{self.model_name}/validate'], type='http', auth="none", methods=['POST'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def validate(self, **kw):
        return self.base_route.validate(**kw)

    @http.route(['/api/{self.model_name}/metadata'], type='http', auth="none", methods=['GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def metadata(self, **kw):
        return self.base_route.metadata(**kw)

    @http.route(['/api/{self.model_name}/state/<int:id>'], type='http', auth="none", methods=['POST', 'PUT'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def change_state(self, id, **kw):
        return self.base_route.change_state(id, **kw)
        
    @http.route(['/api/{self.model_name}/state'], type='http', auth="none", methods=['POST', 'PUT'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def mass_change_state(self, **kw):
        return self.base_route.mass_change_state(**kw)
        
{self.generate_foreign_route()}

"""
        return str_route
