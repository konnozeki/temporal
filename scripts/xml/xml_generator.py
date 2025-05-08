import pandas as pd
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import xml.dom.minidom as minidom
import re
import os

TYPE_CONFIG = {
    "số nguyên lớn": "integer",
    "text": "varchar",
    "double": "float",
    "ký tự": "varchar",
    "datetime": "date",
}

NOT_NULL_CONFIG = {
    "c": "1",
    "k": "0",
}

SKIP_FIELDS = {"created_date", "write_date", "deleted_date", "example", "active"}


class XmlGenerator:
    def __init__(self, excel_file_path: str, prefix: str = "hrm_att"):
        self.excel_file_path = excel_file_path
        self.prefix = prefix
        self.excel = pd.ExcelFile(excel_file_path)

    def _dataframe_to_xml(self, df: pd.DataFrame, model: str) -> str:
        root = ET.Element("root")

        ET.SubElement(root, "model").text = model.lower()
        ET.SubElement(root, "searchable_list").text = "code,name"
        ET.SubElement(root, "default_order").text = "id"

        fields_elem = ET.SubElement(root, "fields")

        for _, row in df.iterrows():
            name = str(row.get("Name", "")).strip()
            if name and name not in SKIP_FIELDS:
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

                    if tag == "reference" and val != "Khóa chính":
                        fk = ET.SubElement(field_elem, "foreign_key")
                        fk.text = f"{val},id,code,name"

        xml_bytes = ET.tostring(root, encoding="UTF-8")
        return minidom.parseString(xml_bytes).toprettyxml(indent="    ")

    def generate_xml(self) -> dict:
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

            clean_name = re.sub(r"[0-9]+\.?\s*", "", sheet_name).lower()
            model_name = f"{self.prefix}_{re.sub('.xlsx', '', clean_name)}"
            xml_string = self._dataframe_to_xml(df, model=model_name)
            result[model_name] = xml_string

        return result
