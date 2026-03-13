from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from temporalio import activity
from config.configuration import BACKEND_ADDON_MAP, BACKEND_ADDONS_ROOT


def _normalize_bool(value, default: bool = False) -> bool:
    """
    Chuẩn hóa một giá trị bất kỳ về boolean.

    - `None` trả về `default`.
    - `bool` giữ nguyên.
    - Các chuỗi truthy thông dụng như `1`, `true`, `yes`, `on` được xem là `True`.

    Hàm này được dùng để đọc các cờ cấu hình truyền qua `kw` từ workflow
    mà không phụ thuộc chặt vào kiểu dữ liệu đầu vào.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _append_missing_lines(file_path: Path, lines: list[str]) -> None:
    """
    Thêm các dòng import còn thiếu vào cuối file.

    - Không ghi trùng nếu dòng đã tồn tại.
    - Tự tạo nội dung mới nếu file chưa có.
    - Giữ cách ghi đơn giản để phù hợp với các file `__init__.py`
      vốn chủ yếu chỉ chứa danh sách import tuần tự.
    """
    existing = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
    existing_lines = {line.strip() for line in existing.splitlines()}
    to_add = [line for line in lines if line.strip() not in existing_lines]
    if not to_add:
        return

    content = existing.rstrip()
    if content:
        content += "\n"
    content += "\n".join(to_add) + "\n"
    file_path.write_text(content, encoding="utf-8")


def _update_annotation_file(annotation_path: Path, entries: list[tuple[str, str]]) -> None:
    """
    Cập nhật file `annotations.py` cho thư mục model đích.

    File này được generator model sử dụng để khai báo `TYPE_CHECKING`,
    phục vụ type hint giữa các model mà không tạo vòng import ở runtime.

    Hàm sẽ:
    - bảo đảm có header chuẩn gồm `from __future__ import annotations`
      và khối `if TYPE_CHECKING:`,
    - chèn thêm các import model còn thiếu,
    - không tạo dòng trùng lặp.
    """
    header = "from __future__ import annotations\nfrom typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n"
    if annotation_path.exists():
        content = annotation_path.read_text(encoding="utf-8")
    else:
        content = header

    if "if TYPE_CHECKING:" not in content:
        content = content.rstrip()
        if content:
            content += "\n\n"
        content += "if TYPE_CHECKING:\n"

    existing_lines = {line.strip() for line in content.splitlines()}
    missing_lines = [f"    from .{module_name}_model import {class_name}" for module_name, class_name in entries if f"from .{module_name}_model import {class_name}" not in existing_lines]

    if not missing_lines:
        return

    lines = content.splitlines()
    insert_index = next((idx + 1 for idx, line in enumerate(lines) if line.strip() == "if TYPE_CHECKING:"), len(lines))
    while insert_index < len(lines) and lines[insert_index].startswith("    "):
        insert_index += 1

    updated_lines = lines[:insert_index] + missing_lines + lines[insert_index:]
    annotation_path.write_text("\n".join(updated_lines).rstrip() + "\n", encoding="utf-8")


def _class_name_for_model(model_name: str) -> str:
    """
    Chuyển technical model name sang tên class Python mà generator đang dùng.

    Ví dụ:
    - `fin_sa_invoice` -> `Fin_Sa_Invoice`
    """
    return model_name.replace("_", " ").title().replace(" ", "_")


def _resolve_target_root(system_code: str) -> Path:
    """
    Resolve thư mục addon đích từ `system_code`.

    Nguồn mapping lấy từ env thông qua `BACKEND_ADDON_MAP` và
    root chung `BACKEND_ADDONS_ROOT`.

    Ví dụ:
    - `FIN` -> `<BACKEND_ADDONS_ROOT>/odoo_addon_fintech`
    - `HRM` -> `<BACKEND_ADDONS_ROOT>/odoo_addon_hrm`

    Raise `ValueError` nếu `system_code` không nằm trong mapping.
    """
    normalized_code = str(system_code).strip().upper()
    addon_name = BACKEND_ADDON_MAP.get(normalized_code)
    if not addon_name:
        raise ValueError(f"Unsupported system_code for backend deploy: {normalized_code}")
    return Path(BACKEND_ADDONS_ROOT).expanduser().resolve() / addon_name


def _resolve_black_command() -> list[str] | None:
    """
    Tìm command khả dụng để chạy Black formatter.

    Thứ tự ưu tiên:
    1. Binary `black` trong PATH.
    2. `python3 -m black`
    3. `python -m black`

    Trả về `None` nếu môi trường hiện tại không có Black khả dụng.
    """
    black_binary = shutil.which("black")
    if black_binary:
        return [black_binary]

    for python_cmd in ("python3", "python"):
        python_binary = shutil.which(python_cmd)
        if not python_binary:
            continue
        probe = subprocess.run([python_binary, "-m", "black", "--version"], capture_output=True, text=True)
        if probe.returncode == 0:
            return [python_binary, "-m", "black"]

    return None


def _format_with_black(root: Path, files: list[Path], enabled: bool = True) -> dict:
    """
    Format các file Python vừa được sinh bằng Black tại root repo đích.

    - `root`: thư mục repo addon, cũng là nơi Black sẽ tự dò `pyproject.toml`.
    - `files`: danh sách file cần format.
    - `enabled`: cho phép tắt format qua cờ cấu hình.

    Kết quả trả về là metadata nhẹ để workflow có thể báo lại:
    - `completed` nếu format thành công,
    - `skipped` nếu tắt formatter, không có file, hoặc môi trường thiếu Black,
    - `error` nếu Black chạy nhưng thất bại.
    """
    if not enabled:
        return {"status": "skipped", "reason": "format_generated_code=false"}

    existing_files = [str(file_path) for file_path in files if file_path.exists()]
    if not existing_files:
        return {"status": "skipped", "reason": "no files to format"}

    black_command = _resolve_black_command()
    if not black_command:
        return {"status": "skipped", "reason": "black is not installed in the current environment"}

    run_result = subprocess.run(
        [*black_command, *existing_files],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if run_result.returncode != 0:
        return {
            "status": "error",
            "command": " ".join(black_command),
            "stderr": run_result.stderr.strip(),
            "stdout": run_result.stdout.strip(),
        }

    return {
        "status": "completed",
        "command": " ".join(black_command),
        "formatted_files": existing_files,
        "stdout": run_result.stdout.strip(),
    }


@activity.defn
async def deploy_backend_artifacts(artifacts: list[dict], kw: dict | None = None) -> dict:
    """
    Triển khai các backend artifacts đã sinh vào đúng Odoo addon workspace.

    - Đầu vào:
      - `artifacts`: danh sách model đã sinh, mỗi phần tử chứa ít nhất
        `model_name`, `system_code`, `model`, `controller`, `route`, `view`.
      - `kw`: cấu hình tùy chọn cho bước deploy, ví dụ:
        - `deploy_generated_code`
        - `system_code` mặc định nếu artifact không có
        - override các thư mục con như `model_subdir`, `route_subdir`, ...

    - Hành vi:
      1. Nhóm artifact theo `system_code`.
      2. Resolve addon đích bằng env mapping.
      3. Ghi file model/controller/route/view vào đúng thư mục.
      4. Cập nhật các `__init__.py`.
      5. Cập nhật `annotations.py` cho model.

    - Kết quả:
      - Trả về metadata gồm danh sách file đã ghi, các target đã deploy,
        và trạng thái format Black nếu có bật formatter.

    - Lỗi:
      - Raise `ValueError` nếu thiếu hoặc không hỗ trợ `system_code`.
      - Raise `FileNotFoundError` nếu thư mục addon đích không tồn tại trong workspace.

    Activity này được chạy bởi workflow deploy riêng, nhằm tách biệt hoàn toàn
    bước sinh mã với bước đưa code vào workspace. Vì vậy nếu deploy lỗi, workflow
    sinh code chính vẫn có thể hoàn tất và trả file ZIP để người dùng import thủ công.
    """
    options = kw or {}
    if not _normalize_bool(options.get("deploy_generated_code", True), True):
        return {"status": "skipped", "reason": "deploy_generated_code=false"}

    layout = {
        "model_dir": Path(options.get("model_subdir", "models/implemented_class")),
        "controller_dir": Path(options.get("controller_subdir", "controllers/implemented_class")),
        "route_dir": Path(options.get("route_subdir", "routes/implemented_class")),
        "view_dir": Path(options.get("view_subdir", "models/views/implemented_class")),
    }
    format_generated_code = _normalize_bool(options.get("format_generated_code", True), True)
    default_system_code = str(options.get("system_code", "")).strip().upper()
    grouped_artifacts: dict[str, list[dict]] = {}

    for artifact in artifacts:
        system_code = str(artifact.get("system_code") or default_system_code).strip().upper()
        if not system_code:
            raise ValueError(f"Missing system_code for model {artifact['model_name']}")
        grouped_artifacts.setdefault(system_code, []).append(artifact)

    written_files: list[str] = []
    targets: list[dict] = []
    format_results: list[dict] = []

    for system_code, system_artifacts in grouped_artifacts.items():
        root = _resolve_target_root(system_code)
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Resolved target module path does not exist or is not a directory: {root}")

        for relative_dir in layout.values():
            (root / relative_dir).mkdir(parents=True, exist_ok=True)

        model_modules: list[str] = []
        controller_modules: list[str] = []
        route_modules: list[str] = []
        view_modules: list[str] = []
        annotation_entries: list[tuple[str, str]] = []
        files_to_format: list[Path] = []

        for artifact in system_artifacts:
            model_name = artifact["model_name"]
            class_name = artifact.get("class_name") or _class_name_for_model(model_name)

            files_to_write = [
                (root / layout["model_dir"] / f"{model_name}_model.py", artifact["model"]),
                (root / layout["controller_dir"] / f"{model_name}_controller.py", artifact["controller"]),
                (root / layout["route_dir"] / f"{model_name}_route.py", artifact["route"]),
                (root / layout["view_dir"] / f"{model_name}_view.py", artifact["view"]),
            ]

            for file_path, content in files_to_write:
                file_path.write_text(content.rstrip() + "\n", encoding="utf-8")
                written_files.append(str(file_path))
                files_to_format.append(file_path)

            model_modules.append(f"{model_name}_model")
            controller_modules.append(f"{model_name}_controller")
            route_modules.append(f"{model_name}_route")
            view_modules.append(f"{model_name}_view")
            annotation_entries.append((model_name, class_name))

        model_init_path = root / layout["model_dir"] / "__init__.py"
        controller_init_path = root / layout["controller_dir"] / "__init__.py"
        route_init_path = root / layout["route_dir"] / "__init__.py"
        view_init_path = root / layout["view_dir"] / "__init__.py"
        models_root_init_path = root / "models" / "__init__.py"
        controllers_root_init_path = root / "controllers" / "__init__.py"
        routes_root_init_path = root / "routes" / "__init__.py"
        views_root_init_path = root / "models" / "views" / "__init__.py"

        _append_missing_lines(model_init_path, [f"from . import {module_name}" for module_name in model_modules])
        _append_missing_lines(controller_init_path, [f"from . import {module_name}" for module_name in controller_modules])
        _append_missing_lines(route_init_path, [f"from . import {module_name}" for module_name in route_modules])
        _append_missing_lines(view_init_path, [f"from . import {module_name}" for module_name in view_modules])

        _append_missing_lines(models_root_init_path, ["from .implemented_class import *", "from .views import *"])
        _append_missing_lines(controllers_root_init_path, ["from .implemented_class import *"])
        _append_missing_lines(routes_root_init_path, ["from .implemented_class import *"])
        _append_missing_lines(views_root_init_path, ["from .implemented_class import *"])

        annotation_path = root / layout["model_dir"] / "annotations.py"
        _update_annotation_file(annotation_path, annotation_entries)
        files_to_format.extend(
            [
                model_init_path,
                controller_init_path,
                route_init_path,
                view_init_path,
                models_root_init_path,
                controllers_root_init_path,
                routes_root_init_path,
                views_root_init_path,
                annotation_path,
            ]
        )

        format_result = _format_with_black(root, files_to_format, enabled=format_generated_code)
        format_result["system_code"] = system_code
        format_results.append(format_result)

        targets.append(
            {
                "system_code": system_code,
                "target_module_path": str(root),
                "models": [artifact["model_name"] for artifact in system_artifacts],
                "format_result": format_result,
            }
        )

    return {
        "status": "completed",
        "targets": targets,
        "format_results": format_results,
        "written_files": written_files,
        "models": [artifact["model_name"] for artifact in artifacts],
    }
