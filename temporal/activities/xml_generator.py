# activities/xml_generator.py
import xml.etree.ElementTree as ET
from temporalio import activity
from scripts.xml.xml_generator import XmlGenerator


@activity.defn
async def generate_xml(excel_data):
    return XmlGenerator(excel_data).generate_xml()
