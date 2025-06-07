# activities/xml_generator.py
import xml.etree.ElementTree as ET
from temporalio import activity
from scripts.xml.xml_generator import XmlGenerator
import pandas as pd
import io


@activity.defn
async def generate_xml(file_bytes: bytes, kw) -> dict:
    excel = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
    generator = XmlGenerator(excel)
    return generator.generate_xml(kw)
