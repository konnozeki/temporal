from config import *


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

        except Exception as e:
            print(e)
            print("Định dạng tệp xml chưa đúng")
            return None

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
from ...config import config as me
from ...controllers.implemented_class.{self.model_name}_controller import {self.class_name}_API
from ...middleware.authentication import Authentication
from ..base_class.nagaco_route import Nagaco_Route


class {self.class_name}_Router(http.Controller):
    def __init__(self):
        self.base_route = Nagaco_Route(me.SYS_CODE, "{self.sub_system_code}", "{self.module_code}", {self.class_name}_API())
        self.AUTH_MODE = self.base_route.AUTH_MODE
        self.ACTION_CODE = self.base_route.ACTION_CODE

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

"""
        return str_route
