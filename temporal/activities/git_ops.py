import os

from sqlalchemy import select
from temporalio import activity

from api.services.git_service import get_git_service
from db.models import XmlFile
from db.session import async_session

@activity.defn
async def sync_db_to_git() -> dict:
    git = get_git_service()

    async with async_session() as session:
        result = await session.execute(select(XmlFile))
        records = result.scalars().all()

    repo_files = git.list_repo_xml_files()
    desired_files: dict[str, str] = {}
    written_paths: list[str] = []

    for record in records:
        system = (record.system or record.filename.split("_")[0]).lower()
        file_path = git.write_file(
            content_id=str(record.id),
            filename=record.filename,
            content=record.content or "",
            system=system,
        )
        relative_path = os.path.relpath(file_path, git.repo_path)
        desired_files[relative_path] = relative_path
        written_paths.append(relative_path)

    deleted_paths: list[str] = []
    for relative_path, repo_file in repo_files.items():
        if relative_path not in desired_files:
            full_path = os.path.join(git.repo_path, repo_file["relative_path"])
            if os.path.exists(full_path):
                os.remove(full_path)
            deleted_paths.append(repo_file["relative_path"])

    changed_paths = written_paths + deleted_paths
    if not changed_paths:
        return {"direction": "db_to_git", "changed_files": [], "commit_created": False}

    if written_paths:
        git.repo.index.add(written_paths)
    if deleted_paths:
        git.repo.index.remove(deleted_paths, working_tree=True)

    if git.repo.is_dirty(untracked_files=True):
        git.repo.index.commit("Sync XML files from DB to Git")
        git.push_all()
        return {"direction": "db_to_git", "changed_files": changed_paths, "commit_created": True}

    return {"direction": "db_to_git", "changed_files": [], "commit_created": False}


@activity.defn
async def sync_git_to_db() -> dict:
    git = get_git_service()
    repo_files = git.list_repo_xml_files()

    async with async_session() as session:
        result = await session.execute(select(XmlFile))
        existing_records = result.scalars().all()
        existing_by_path = {
            git.build_relative_path(record.filename, (record.system or record.filename.split("_")[0]).lower()): record for record in existing_records
        }

        imported: list[str] = []
        updated: list[str] = []
        deleted: list[str] = []
        seen_paths: set[str] = set()

        for relative_path, repo_file in repo_files.items():
            filename = repo_file["filename"]
            content = repo_file["content"]
            system, sub_system, module_code, category = await _extract_system_info(content)
            seen_paths.add(relative_path)

            existing = existing_by_path.get(relative_path)
            if existing is None:
                session.add(
                    XmlFile(
                        filename=filename,
                        content=content,
                        system=system,
                        sub_system=sub_system,
                        module=module_code,
                        category=category,
                    )
                )
                imported.append(relative_path)
                continue

            changed = any(
                [
                    existing.filename != filename,
                    (existing.content or "") != content,
                    existing.system != system,
                    existing.sub_system != sub_system,
                    existing.module != module_code,
                    existing.category != category,
                ]
            )
            existing.filename = filename
            existing.content = content
            existing.system = system
            existing.sub_system = sub_system
            existing.module = module_code
            existing.category = category
            if changed:
                updated.append(relative_path)

        for relative_path, record in existing_by_path.items():
            if relative_path in seen_paths:
                continue
            await session.delete(record)
            deleted.append(relative_path)

        await session.commit()

    return {"direction": "git_to_db", "imported_files": imported, "updated_files": updated, "deleted_files": deleted}


async def _extract_system_info(xml_content: str):
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml_content)
        return root.find("system_code").text, root.find("sub_system_code").text, root.find("module_code").text, root.find("module").text
    except Exception:
        return None, None, None, None
