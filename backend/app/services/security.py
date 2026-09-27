"""安防巡视业务规则：巡视区域读取、异常统计与处理入口共用同一份数据口径。

所有安防记录的筛选、明细与动作都以 ``_query_rows`` 为唯一数据来源，
列表、区域概览、异常统计和处理动作不再各自扫表、各自定口径；
缺少「处理情况」的记录也照常进入查询结果，不被过滤掉。
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.store import store

MODULE = "security"
REQUIRED_FIELDS = ["巡视编号", "巡视区域", "巡视人员"]
STATUS_ORDER = ["已排班", "巡视中", "正常完成", "发现异常"]
ACTION_RULES = {"开始巡视": "巡视中", "记录异常": "发现异常", "完成巡视": "正常完成"}
# 只有正常完成才退出待巡视；发现异常仍需跟进，继续计入待巡视区域。
DONE_STATUSES = ["正常完成"]

AREA_FIELD = "巡视区域"
INSPECTOR_FIELD = "巡视人员"
HANDOVER_FIELD = "交接事项"
TIME_FIELD = "巡视时间"
ABNORMAL_STATUS = "发现异常"


def _has_text(value: Any) -> bool:
    """判断字段是否有可读内容：None、空串、纯空白都算空数据。"""
    return bool(str(value or "").strip())


class SecurityService:
    def _query_rows(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        area: str | None = None,
        inspector: str | None = None,
    ) -> list[dict[str, Any]]:
        """安防记录唯一数据来源：区域读取、异常统计、处理入口都从这里取数。

        只按编号、状态、巡视区域、巡视人员收敛范围，绝不依赖「处理情况」，
        因此尚未填写处理情况的巡视记录仍然能被查到。
        """
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("巡视编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        if area:
            rows = [row for row in rows if area == str(row.get(AREA_FIELD, "")).strip()]
        if inspector:
            rows = [row for row in rows if inspector in str(row.get(INSPECTOR_FIELD, ""))]
        return rows

    @staticmethod
    def _is_abnormal(row: dict[str, Any]) -> bool:
        """异常统计口径：标记为异常或已流转到「发现异常」状态都计入。"""
        return bool(row.get("abnormal")) or row.get("status") == ABNORMAL_STATUS

    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        area: str | None = None,
        inspector: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = self._query_rows(keyword=keyword, status=status, area=area, inspector=inspector)
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def area_overview(self) -> list[dict[str, Any]]:
        """巡视区域读取入口：按区域汇总巡视量、异常量、待处理量。

        巡视人员与交接事项随区域一起给出，前端各入口共用这一份。
        """
        overview: dict[str, dict[str, Any]] = {}
        for row in self._query_rows():
            name = str(row.get(AREA_FIELD, "")).strip() or "未划分区域"
            bucket = overview.setdefault(
                name,
                {"area": name, "total": 0, "abnormal": 0, "pending": 0,
                 "inspectors": set(), "handover_items": []},
            )
            bucket["total"] += 1
            if self._is_abnormal(row):
                bucket["abnormal"] += 1
            if row.get("pending"):
                bucket["pending"] += 1
            inspector = str(row.get(INSPECTOR_FIELD, "")).strip()
            if inspector:
                bucket["inspectors"].add(inspector)
            handover = row.get(HANDOVER_FIELD)
            if _has_text(handover):
                bucket["handover_items"].append(str(handover).strip())
        return [
            {
                "area": bucket["area"],
                "total": bucket["total"],
                "abnormal": bucket["abnormal"],
                "pending": bucket["pending"],
                "inspectors": sorted(bucket["inspectors"]),
                "handover_items": bucket["handover_items"],
            }
            for bucket in sorted(overview.values(), key=lambda item: item["area"])
        ]

    def stats(self) -> dict[str, int]:
        """异常统计入口：今日巡视、异常巡视、待巡视区域三项共用记录口径。"""
        today = date.today().isoformat()
        rows = self._query_rows()
        pending_areas = {
            str(row.get(AREA_FIELD, "")).strip() or "未划分区域"
            for row in rows
            if row.get("pending")
        }
        return {
            "today": sum(1 for row in rows if str(row.get(TIME_FIELD, ""))[:10] == today),
            "abnormal": sum(1 for row in rows if self._is_abnormal(row)),
            "pending_areas": len(pending_areas),
        }

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
        """处理入口：开始巡视、记录异常、完成巡视都在这里落地状态。"""
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"安防记录 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于安防巡视可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target not in DONE_STATUSES
        entry["abnormal"] = self._is_abnormal({**entry, "status": target})
        return entry, f"安防记录已{action}"
