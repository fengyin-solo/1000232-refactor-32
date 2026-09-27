"""安防巡视业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.store import store

MODULE = "security"
REQUIRED_FIELDS = ["巡视编号", "巡视区域", "巡视人员"]
STATUS_ORDER = ["已排班", "巡视中", "正常完成", "发现异常"]
ACTION_RULES = {"开始巡视": "巡视中", "记录异常": "发现异常", "完成巡视": "正常完成"}
NEGATIVE_ACTIONS = []

# 巡视区域读取、异常统计、处理入口共用同一份筛选口径：查询参数 -> 业务字段。
FILTER_FIELDS = {
    "keyword": "巡视编号",
    "area": "巡视区域",
    "operator": "巡视人员",
    "handling": "处理情况",
    "handover": "交接事项",
}


class SecurityService:
    def _filtered_rows(self, filters: dict[str, str | None]) -> list[dict[str, Any]]:
        """各入口共用的数据来源：同一份安防记录、同一套匹配规则。

        字段缺失（如处理情况未填）按空串参与匹配，缺少处理情况的记录仍能查到。
        """
        rows = store.rows(MODULE)
        for param, field in FILTER_FIELDS.items():
            expected = str(filters.get(param) or "").strip()
            if expected:
                rows = [row for row in rows if expected in str(row.get(field) or "")]
        status = str(filters.get("status") or "").strip()
        if status:
            rows = [row for row in rows if row.get("status") == status]
        return rows

    def list_entries(
        self,
        *,
        filters: dict[str, str | None] | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = self._filtered_rows(filters or {})
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def summarize(self, *, filters: dict[str, str | None] | None = None) -> list[dict[str, Any]]:
        """异常统计：与列表走同一份筛选结果，避免两处口径各自维护。"""
        rows = self._filtered_rows(filters or {})
        today = date.today().isoformat()
        pending_areas = {str(row.get("巡视区域") or "").strip() for row in rows if row.get("pending")}
        pending_areas.discard("")
        return [
            {"label": "今日巡视", "value": sum(1 for row in rows if str(row.get("巡视时间") or "") == today)},
            {"label": "异常巡视", "value": sum(1 for row in rows if row.get("abnormal") or row.get("status") == STATUS_ORDER[-1])},
            {"label": "待巡视区域", "value": len(pending_areas)},
        ]

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"安防记录 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于安防巡视可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"安防记录已{action}"
