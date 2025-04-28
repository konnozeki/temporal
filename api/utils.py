import os
import shutil
import tempfile
import zipfile
from fastapi.responses import FileResponse


async def save_multiple_files(files: dict, extension: str) -> str:
    # files: dict {filename: file_content}
    temp_dir = tempfile.mkdtemp()
    for filename, content in files.items():
        file_path = os.path.join(temp_dir, f"{filename}.{extension}")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    # Tạo file zip
    zip_path = f"{temp_dir}.zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_full_path = os.path.join(root, file)
                zipf.write(file_full_path, arcname=file)

    # Xóa folder tạm sau khi zip
    shutil.rmtree(temp_dir)

    return zip_path
