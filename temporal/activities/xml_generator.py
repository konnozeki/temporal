# activities/xml_generator.py
import xml.etree.ElementTree as ET
from temporalio import activity


@activity.defn
async def excel_to_xml(excel_data: str):
    # Logic giả định: Chuyển đổi dữ liệu Excel thành XML
    # (Giả sử excel_data là một chuỗi JSON hoặc CSV đã được cung cấp)

    # Tạo một file XML giả định từ excel_data
    root = ET.Element("Root")
    item = ET.SubElement(root, "Item")
    item.set("name", excel_data)
    item.text = "Generated from Excel to XML"

    # Tạo tree XML và chuyển thành chuỗi
    tree = ET.ElementTree(root)
    xml_data = ET.tostring(root, encoding="unicode", method="xml")

    return xml_data
