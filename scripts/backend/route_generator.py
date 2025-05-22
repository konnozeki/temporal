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
            for field in xml_dict["root"]["fields"]["field"]:
                if field is None:
                    continue
                if "foreign_key" in field and field["foreign_key"] and len(field["foreign_key"].strip()) > 0:
                    fk_items = field["foreign_key"].strip().replace(" ", "").split(",")
                    if fk_items[0]:
                        fk_list.append(re.sub("^nagaco_|^hrm_|^fin_", "", fk_items[0]))
            self.foreign_keys = fk_list

        except Exception as e:
            print(e)
            print("Định dạng tệp xml chưa đúng")
            return None

    def generate_foreign_route(self):
        route_str = ""
        for fk_name in self.foreign_keys:
            route_str += f"""
    @http.route(['/api/{self.model_name}/{fk_name}'], type='http', auth="none", methods=['GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def get_all_by_{fk_name}(self, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-R")
            if code != 200:
                return res
            code, _, _ = Authentication.verify(f"{{self.ACTION_CODE}}-A") # Check user can Approval
            if code == 200:
                return self.ctrl.get_all_by('{fk_name}', user=auth['data']['user'], approval=True, **kw)
            return self.ctrl.get_all_by('{fk_name}', user=auth['data']['user'], **kw)
        return self.ctrl.get_all_by('{fk_name}', **kw)
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


class {self.class_name}_Router(http.Controller):
    def __init__(self):
        self.SYS_CODE = me.SYS_CODE
        self.SUB_SYS_CODE = '{self.sub_system_code}'
        self.MODULE_CODE = '{self.module_code}'
        self.AUTH_MODE = me.AUTH_MODE
        self.ACTION_CODE = f"{{self.SYS_CODE}}_{{self.SUB_SYS_CODE}}-{{self.MODULE_CODE}}"
        self.ctrl = {self.class_name}_API()

    @http.route(['/api/{self.model_name}'], type='http', auth="none", methods=['GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def get_all(self, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-R")
            if code != 200:
                return res
            code, _, _ = Authentication.verify(f"{{self.ACTION_CODE}}-A") # Check user can Approval
            if code == 200:
                return self.ctrl.get_all(user = auth['data']['user'], approval = True, **kw)
            return self.ctrl.get_all(user = auth['data']['user'], **kw)
        return self.ctrl.get_all(**kw)

    @http.route(['/api/{self.model_name}/page/<int:page>/'], type='http', auth="none", methods=['GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def get_by_page(self,page, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-R")
            if code != 200:
                return res
            code, _, _ = Authentication.verify(f"{{self.ACTION_CODE}}-A") # Check user can Approval
            if code == 200:
                return self.ctrl.get_by_page(page, user = auth['data']['user'], approval = True, **kw)
            return self.ctrl.get_by_page(page, user = auth['data']['user'], **kw)
        return self.ctrl.get_by_page(page, **kw)

    @http.route(['/api/{self.model_name}/<int:id>'], type='http', auth="none", methods=['GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def get_by_id(self, id, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-R")
            if code != 200:
                return res
            return self.ctrl.get_by_id(id, user = auth['data']['user'], **kw)
        return self.ctrl.get_by_id(id, **kw)

    @http.route(['/api/{self.model_name}'], type='http', auth="none", methods=['POST'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def store(self, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-C")
            if code != 200:
                return res
            code, _, _ = Authentication.verify(f"{{self.ACTION_CODE}}-A") # Check user can Approval
            if code == 200:
                return self.ctrl.store(user = auth['data']['user'], approval = True, **kw)
            return self.ctrl.store(user = auth['data']['user'], **kw)
        return self.ctrl.store(**kw)

    @http.route(['/api/{self.model_name}/<int:id>'], type='http', auth="none", methods=['POST', 'PUT'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def update(self, id, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-U")
            if code != 200:
                return res
            return self.ctrl.update(id, user = auth['data']['user'], **kw)
        return self.ctrl.update(id, **kw)

    @http.route(['/api/{self.model_name}/<int:id>'], type='http', auth="none", methods=['DELETE'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def destroy(self, id, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-D")
            if code != 200:
                return res
            return self.ctrl.destroy(id, user = auth['data']['user'], **kw)
        return self.ctrl.destroy(id, **kw)

    @http.route(['/api/{self.model_name}/copy'], type='http', auth="none", methods=['POST'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def mass_copy(self, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-V")
            if code != 200:
                return res
            return self.ctrl.mass_copy(user = auth['data']['user'], **kw)
        return self.ctrl.mass_copy(**kw)

    @http.route(['/api/{self.model_name}/delete'], type='http', auth="none", methods=['DELETE'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def mass_delete(self, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-D")
            if code != 200:
                return res
            return self.ctrl.mass_delete(user = auth['data']['user'], **kw)
        return self.ctrl.mass_delete(**kw)

    @http.route(['/api/{self.model_name}/import'], type='http', auth="none", methods=['POST'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def import_data(self, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-I")
            if code != 200:
                return res
            return self.ctrl.import_data(user = auth['data']['user'], **kw)
        return self.ctrl.import_data(**kw)

    @http.route(['/api/{self.model_name}/import'], type='http', auth="none", methods=['GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def get_template_import(self, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-R")
            if code != 200:
                return res
            return self.ctrl.get_template_import(user = auth['data']['user'], **kw)
        return self.ctrl.get_template_import(**kw)

    @http.route(['/api/{self.model_name}/export/<int:id>'], type='http', auth="none", methods=['POST', 'GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def export_by_id(self, id, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-E")
            if code != 200:
                return res
            return self.ctrl.export_by_id(id, user = auth['data']['user'], **kw)
        return self.ctrl.export_by_id(id, **kw)

    @http.route(['/api/{self.model_name}/export'], type='http', auth="none", methods=['POST', 'GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def mass_export(self, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-E")
            if code != 200:
                return res
            return self.ctrl.mass_export(user = auth['data']['user'], **kw)
        return self.ctrl.mass_export(**kw)

    @http.route(['/api/{self.model_name}/help'], type='http', auth="none", methods=['GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def help(self, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-R")
            if code != 200:
                return res
            return self.ctrl.help(user = auth['data']['user'], **kw)
        return self.ctrl.help(**kw)

    @http.route(['/api/{self.model_name}/validate'], type='http', auth="none", methods=['POST'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def validate(self, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-R")
            if code != 200:
                return res
            return self.ctrl.validate(user = auth['data']['user'], **kw)
        return self.ctrl.validate(**kw)

    @http.route(['/api/{self.model_name}/metadata'], type='http', auth="none", methods=['GET'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def metadata(self, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-R")
            if code != 200:
                return res
            return self.ctrl.metadata(user = auth['data']['user'], **kw)
        return self.ctrl.metadata(**kw)

    @http.route(['/api/{self.model_name}/state/<int:id>'], type='http', auth="none", methods=['POST', 'PUT'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def change_state(self, id, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-A")
            if code != 200:
                return res
            return self.ctrl.change_state(id, user = auth['data']['user'], **kw)
        return self.ctrl.change_state(id, **kw)
        
    @http.route(['/api/{self.model_name}/state'], type='http', auth="none", methods=['POST', 'PUT'], sitemap=me.sitemap, cors=me.cors, csrf=me.csrf)
    def mass_change_state(self, **kw):
        auth = None
        if self.AUTH_MODE:
            code, res, auth = Authentication.verify(f"{{self.ACTION_CODE}}-A")
            if code != 200:
                return res
            return self.ctrl.mass_change_state(user = auth['data']['user'], **kw)
        return self.ctrl.mass_change_state(**kw)
        
{self.generate_foreign_route()}

"""
        return str_route
