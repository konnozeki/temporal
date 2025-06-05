import re


class I18nGenerator:
    """
    Lớp `I18nGenerator` dùng để sinh ra chuỗi localization (`i18n`) dạng JSON cho cả tiếng Việt (vi) và tiếng Anh (en),
    từ metadata định nghĩa field của một model.

    ### Mục đích:
    - Tự động sinh các cặp key-value bản địa hóa cho UI (label, message, button...).
    - Chuẩn hóa theo định dạng `{ "field_name": "Nhãn" }`.

    ### Thuộc tính:
    - `xml_dict` (dict): Metadata được parse từ XML.
    - `prefix` (str): Tiền tố cần loại bỏ khỏi tên model (nếu có), thường là `nagaco_`.
    """

    def __init__(self, xml_dict, prefix=""):
        self.xml_dict = xml_dict
        self.prefix = prefix

    def generate(self):
        """
        Sinh ra cặp chuỗi JSON cho tiếng Việt và tiếng Anh.

        ### Cách hoạt động:
        - Trích xuất `model_name` và các `field` từ `xml_dict["root"]`.
        - Với mỗi trường:
            + Lấy `name`, `label` để xây key-value tương ứng.
            + Với `foreign key`, tạo thêm định danh dạng `name`, `code` nếu có.
        - Tự động tạo thêm các key chuẩn UI như:
            + `add_new_<model>`, `edit_<model>`, `search_<model>`, `import_<model>_record`, v.v.
        - Sử dụng `.format(class_name)` để chèn tên động vào các thông điệp mẫu.

        ### Trả về:
        - `vn_str`: Chuỗi JSON tiếng Việt (`{ "field_name": "..." }`)
        - `en_str`: Chuỗi JSON tiếng Anh (`{ "field_name": "..." }`)

        ### Ghi chú:
        - Nếu không tìm được label cho field `name` hoặc `code`, sẽ fallback sang `model_name` (dạng snake_case).
        - Dữ liệu trả về có thể copy trực tiếp vào file `vi.json` và `en.json`.

        """
        try:
            model_name = self.xml_dict["root"]["model"].strip()
            fields = self.xml_dict["root"]["fields"]["field"]
            field_list = fields if isinstance(fields, list) else [fields]

            def get_value(field, key, default=""):
                val = field.get(key)
                return default if val is None else val.strip().lower()

            class_name_en = model_name.replace("_", " ").replace(f"{self.prefix} ", "").strip().lower()
            class_name_vn = ""

            translations_vn = {}
            translations_en = {}

            for field in field_list:
                if field is None:
                    continue

                field_name = get_value(field, "name")
                field_label = get_value(field, "label")

                if not field_name:
                    continue

                if not class_name_vn:
                    if field_name == "name":
                        class_name_vn = field_label.replace("tên ", "")
                    elif field_name == "code":
                        class_name_vn = field_label.replace("mã ", "")

                if field_label:
                    field_label = re.sub(r"\s+", " ", field_label).capitalize()
                    translations_vn[field_name] = field_label
                    translations_en[field_name] = field_name.replace("_", " ").capitalize()

            class_name_vn = class_name_vn or class_name_en  # fallback nếu không tìm được

            base_keys = {
                "info_detail": ("Thông tin chi tiết {}", "Information detail {}"),
                "category": ("Danh mục {}", "Category {}"),
                f"add_new_{model_name}": ("Thêm mới {}", "Add new {}"),
                f"edit_{model_name}": ("Sửa {}", "Edit {}"),
                f"search_{model_name}": ("Tìm {}", "Search {}"),
                f"{model_name}_category": ("Danh mục {}", "{} category"),
                f"{model_name}_detail": ("Chi tiết {}", "{} detail"),
                f"import_{model_name}_record": ("Nhập {} từ tệp", "Import {}"),
                f"export_{model_name}_record": ("Xuất {} ra tệp", "Export {}"),
                "adding_not_completed": ("Nhập liệu {} còn đang thực hiện chưa xong!", "{} data entry is still in progress!"),
                "editing_not_completed": ("Chỉnh sửa {} còn đang thực hiện chưa xong!", "Editing the {} is still in progress!"),
                "message_masscopy_data_successfully": ("Sao chép thành công {} đã chọn", "Successfully copied the selected {}(s)"),
                "message_can_edit": ("Có thể hiệu chỉnh lại thông tin {} đã chọn", "Can edit selected {} information"),
                "write_date": ("Thời gian cập nhật cuối cùng", "Write date"),
                "updatedAt": ("Cập nhật lần cuối", "Last updated"),
            }

            for key, (vn_template, en_template) in base_keys.items():
                translations_vn[key] = vn_template.format(class_name_vn)
                translations_en[key] = en_template.format(class_name_en)

            # Build final strings
            vn_str = "{\n\t" + ",\n\t".join(f'"{k}": "{v}"' for k, v in translations_vn.items()) + "\n}"
            en_str = "{\n\t" + ",\n\t".join(f'"{k}": "{v}"' for k, v in translations_en.items()) + "\n}"

            return vn_str, en_str

        except Exception as e:
            return str(e), str(e)
