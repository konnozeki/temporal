from temporalio import activity
from db.session import get_sync_session
from db.models import XmlFile, XmlFileVersion
from datetime import datetime


@activity.defn
async def save_xml_to_db(filename: str, xml_content: str, system: str, sub_system: str) -> int:
    """
    Ghi nội dung XML vào cơ sở dữ liệu.
    """
    session = get_sync_session()

    try:
        xml_file = XmlFile(
            filename=filename,
            system=system,
            sub_system=sub_system,
            status="processing",
            version="v1",
            created_at=datetime.utcnow(),
        )
        session.add(xml_file)
        session.flush()

        version = XmlFileVersion(
            xml_file_id=xml_file.id,
            version="v1",
            content=xml_content,
            approved=False,
        )
        session.add(version)
        session.commit()

        return xml_file.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
