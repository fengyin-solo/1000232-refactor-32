"""安防巡视接口：维护安防记录，覆盖开始巡视、记录异常、完成巡视等动作。

巡视区域读取（/areas）、异常统计（/stats）与处理入口（/{entry_id}/actions）
共用 service 里的同一份记录查询，权限范围与原有接口保持一致，不再各自维护口径。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.security import SecurityService

router = APIRouter(prefix="/api/security", tags=["安防巡视"])

service = SecurityService()

LIST_FIELDS = ["巡视编号", "巡视区域", "巡视人员", "巡视时间", "异常描述", "处理情况", "交接事项", "巡视状态"]
STATUSES = ["已排班", "巡视中", "正常完成", "发现异常"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按巡视编号检索"),
    status: str | None = Query(default=None, description="已排班、巡视中、正常完成、发现异常"),
    area: str | None = Query(default=None, description="按巡视区域精确过滤"),
    inspector: str | None = Query(default=None, description="按巡视人员检索"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按编号、状态、巡视区域与巡视人员过滤列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(
        keyword=keyword, status=status, area=area, inspector=inspector, page=page, size=size,
    )
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/areas")
def list_areas() -> dict[str, Any]:
    """巡视区域读取入口：按区域汇总巡视量、异常量与待处理量，并给出巡视人员和交接事项。

    与列表、统计、处理动作读取同一份安防记录；没有数据时返回空列表，不报错。
    """
    return {"module": "security", "areas": service.area_overview()}


@router.get("/stats")
def get_stats() -> dict[str, Any]:
    """异常统计入口：今日巡视、异常巡视、待巡视区域，口径与列表完全一致。"""
    return {"module": "security", "stats": service.stats()}


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出安防巡视清单：返回当前过滤条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "security", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条安防记录明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"安防记录 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条安防记录，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="安防记录已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """处理入口：对单条安防记录执行开始巡视、记录异常、完成巡视；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
