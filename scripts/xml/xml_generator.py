import pandas as pd
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import xml.dom.minidom as minidom
import re
import os

TYPE_CONFIG = {
    "số nguyên lớn": "integer",
    "text": "text",
    "double": "float",
    "ký tự": "varchar",
    "datetime": "datetime",
    "date": "date",
    "logic": "bool",
    "số thực": "float",
    "số nguyên": "integer",
    "file": "file",
    "image": "file",
}

NOT_NULL_CONFIG = {
    "c": "1",
    "k": "0",
}

SKIP_FIELDS = [
    "created_date",
    "write_date",
    "deleted_date",
    "example",
    "active",
]


class XmlGenerator:
    def __init__(self, excel_file):
        self.excel = excel_file

    def _get_module_code(self, sheet_name: str) -> str:
        module_code = sheet_name.split("_")
        shortened_parts = [part[:3].upper() for part in module_code]
        return "_".join(shortened_parts)

    def _dataframe_to_xml(self, df: pd.DataFrame, model: str, kw: dict) -> str:
        root = ET.Element("root")
        system_code = kw.get("system_code", "SYS")
        sub_system_code = kw.get("sub_system_code", "SUB")
        module_code = self._get_module_code(model.lower().replace(f"{system_code.lower()}_", ""))
        module = kw.get("module", "categories")

        ET.SubElement(root, "system_code").text = system_code
        ET.SubElement(root, "sub_system_code").text = sub_system_code
        ET.SubElement(root, "module").text = module.lower()
        ET.SubElement(root, "module_code").text = module_code

        ET.SubElement(root, "model").text = model.lower()
        ET.SubElement(root, "searchable_list").text = "code,name"
        ET.SubElement(root, "default_order").text = "id"

        fields_elem = ET.SubElement(root, "fields")

        for _, row in df.iterrows():
            name = row.get("Name")
            if not name or pd.isna(name) or str(name).strip() == "" or name in SKIP_FIELDS:
                continue

            name = str(name).strip()
            field_elem = ET.SubElement(fields_elem, "field")

            if name == "id":
                ET.SubElement(field_elem, "primary_key").text = "1"

            for col_name, value in row.items():
                if col_name == "Index" or pd.isna(value):
                    continue

                tag = col_name.lower()
                val = str(value).strip()

                match tag:
                    case "type":
                        val = TYPE_CONFIG.get(val.lower(), "varchar")
                    case "not_null":
                        val = NOT_NULL_CONFIG.get(val.lower(), "0")
                    case _:
                        val = val

                elem = ET.SubElement(field_elem, tag)
                elem.text = escape(val)

                if tag == "reference" and val.lower() != "khóa chính":
                    fk = ET.SubElement(field_elem, "foreign_key")
                    fk.text = f"{val},id,code,name"

                # if tag == "type" and val.lower() == "date":
                #     ET.SubElement(field_elem, "date").text = "1"

        xml_bytes = ET.tostring(root, encoding="UTF-8")
        return minidom.parseString(xml_bytes).toprettyxml(indent="    ")

    def generate_xml(self, kw: dict) -> dict:
        result = {}
        for sheet_name in self.excel.sheet_names:
            if "Sheet" in sheet_name:
                continue

            df = self.excel.parse(sheet_name)
            df.drop(
                df.columns[df.columns.str.contains("unnamed", case=False)],
                axis=1,
                inplace=True,
            )
            prefix = kw.get("system_code", "SYS").lower()
            clean_name = re.sub(r"^[0-9]+\.?\s*", "", sheet_name).lower()
            clean_name = re.sub(f"{prefix}_", "", clean_name)
            # Tạm thời để tên là model nhưng về sau phải đổi từ request.
            model_name = f"{prefix}_{re.sub('.xlsx', '', clean_name)}"
            xml_string = self._dataframe_to_xml(df, model=model_name, kw=kw)
            result[model_name] = xml_string

        return result
