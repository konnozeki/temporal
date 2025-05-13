from temporalio import activity
from db.session import async_session
from db.models import XmlFile, XmlFileVersion
from datetime import datetime
from pathlib import Path
from sqlalchemy import select


@activity.defn
async def save_generated_xml(xml_dict: dict, module: str, version: str = "v1", created_by: str = "system"):
    base_path = Path("xml_store") / module / version
    base_path.mkdir(parents=True, exist_ok=True)
    async with async_session() as session:
        for model_name, xml_string in xml_dict.items():
            filename = f"{model_name}.xml"
            file_path = base_path / filename

            # 1. Lưu file XML
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(xml_string)

            # 2. Tìm hoặc tạo XmlFile
            stmt = select(XmlFile).where(XmlFile.module == module, XmlFile.filename == filename)
            result = await session.execute(stmt)
            xml_file = result.scalar_one_or_none()

            if not xml_file:
                xml_file = XmlFile(filename=filename, module=module, version=version, status="processing")
                session.add(xml_file)
                await session.commit()
                await session.refresh(xml_file)

            # 3. Thêm phiên bản
            version_record = XmlFileVersion(xml_file_id=xml_file.id, version=version, content=xml_string, approved=False)
            session.add(version_record)
            await session.commit()
