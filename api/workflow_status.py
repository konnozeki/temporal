# workflow_status.py
from typing import Dict

# Bộ nhớ tạm tracking trạng thái các workflow
WORKFLOW_STATUS: Dict[str, str] = {}


def set_status(workflow_id: str, status: str):
    WORKFLOW_STATUS[workflow_id] = status


def get_status(workflow_id: str) -> str:
    return WORKFLOW_STATUS.get(workflow_id, "unknown")
