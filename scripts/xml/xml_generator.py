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
        ET.SubElement(root, "default_order").text = "id"

        fields_elem = ET.SubElement(root, "fields")
        searchable_list = []

        for _, row in df.iterrows():
            # Chuẩn hóa tất cả key về lowercase
            row = {str(k).strip().lower(): v for k, v in row.items()}

            name = row.get("name")
            if not name or pd.isna(name) or str(name).strip() == "" or name in SKIP_FIELDS:
                continue

            name = str(name).strip()

            # Check if field is searchable
            searchable_val = str(row.get("searchable", "")).lower().strip()
            if searchable_val in {"1", "c", "t", "d"}:
                searchable_list.append(name)

            field_elem = ET.SubElement(fields_elem, "field")

            if name == "id":
                ET.SubElement(field_elem, "primary_key").text = "1"

            for tag, value in row.items():
                if tag == "index" or pd.isna(value):
                    continue

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
                    serialized_val = row.get("serialized_field", "id,code,name")
                    serialized_val = str(serialized_val).strip() if serialized_val and not pd.isna(serialized_val) else "id,code,name"
                    fk = ET.SubElement(field_elem, "foreign_key")
                    fk.text = f"{val},{serialized_val}"

        ET.SubElement(root, "searchable_list").text = ",".join(searchable_list)

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
