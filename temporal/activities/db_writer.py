from temporalio import activity
from db.session import async_session
from db.models import XmlFile
from sqlalchemy import select
import xmltodict
from api.services.xml_service import XmlService
import os

xml_service = XmlService()
git = xml_service.git


@activity.defn
async def save_generated_xml(xml_dict: dict, category: str):
    async with async_session() as session:
        file_paths = []
        updated_models = []

        for model_name, xml_string in xml_dict.items():
            dict_data = xmltodict.parse(xml_string)
            system_code = dict_data["root"]["system_code"]
            sub_system_code = dict_data["root"]["sub_system_code"]
            module = dict_data["root"]["module_code"]
            filename = f"{model_name}_schema.xml"

            # 1. Tìm hoặc tạo XmlFile
            stmt = select(XmlFile).where(XmlFile.module == module, XmlFile.filename == filename)
            result = await session.execute(stmt)
            xml_file = result.scalar_one_or_none()

            if not xml_file:
                xml_file = XmlFile(
                    filename=filename,
                    system=system_code,
                    sub_system=sub_system_code,
                    module=module,
                    category=category,
                    content=xml_string,
                )
                session.add(xml_file)
            else:
                xml_file.system = system_code
                xml_file.sub_system = sub_system_code
                xml_file.category = category
                xml_file.content = xml_string

            await session.commit()
            await session.refresh(xml_file)

            # 2. Ghi file vào Git (chưa commit ngay)
            file_path = git.write_file(content_id=str(xml_file.id), filename=filename, content=xml_string, system=system_code.lower())
            relative_path = os.path.relpath(file_path, git.repo_path)
            file_paths.append(relative_path)
            updated_models.append(model_name)

        # 3. Gộp commit Git và push
        if file_paths:
            git.repo.index.add(file_paths)
            commit_message = f"Cập nhật schema XML cho các model: {', '.join(updated_models)}"
            git.repo.index.commit(commit_message)
            git.push_all()
