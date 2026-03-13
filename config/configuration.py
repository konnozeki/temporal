import os

"""
Cấu hình chạy chung cho ứng dụng Temporal generator.

Khối cấu hình này bao gồm:
- Kết nối Temporal và database.
- Đường dẫn repo XML đồng bộ với git.
- Cấu hình backend addons root và mapping `system_code -> addon directory`
  dùng cho workflow triển khai code backend sau khi sinh mã.

Các biến `BACKEND_ADDONS_ROOT` và `BACKEND_ADDON_*` được đọc từ environment
để tương thích cả môi trường host lẫn container Docker. Bên trong container,
`BACKEND_ADDONS_ROOT` nên trỏ tới path đã được mount volume, ví dụ
`/workspace/backend-addons`.
"""

CURRENT_PREFIX_LIST = ["nagaco", "hrm", "fin", "man"]

TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "temporal:7233")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://temporal:temporal@postgresql:5432/postgres")
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"
GIT_REPO_PATH = os.getenv("GIT_REPO_PATH", "./xml_repo")
BACKEND_ADDONS_ROOT = os.path.expanduser(os.getenv("BACKEND_ADDONS_ROOT", "~/code/backend/odoo/custom-addons"))
BACKEND_ADDON_MAP = {
    "FOB": os.getenv("BACKEND_ADDON_FOB", "odoo_addon_template"),
    "HRM": os.getenv("BACKEND_ADDON_HRM", "odoo_addon_hrm"),
    "FIN": os.getenv("BACKEND_ADDON_FIN", "odoo_addon_fintech"),
    "RE": os.getenv("BACKEND_ADDON_RE", "odoo_addon_repository"),
    "MES": os.getenv("BACKEND_ADDON_MES", "odoo_addon_mes"),
}
