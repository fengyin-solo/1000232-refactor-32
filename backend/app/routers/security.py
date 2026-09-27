"""安防巡视接口：维护安防记录，覆盖开始巡视、记录异常、完成巡视等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.security import STATUS_ORDER, SecurityService

router = APIRouter(prefix="/api/security", tags=["安防巡视"])

service = SecurityService()

STATUS_HINT = "、".join(STATUS_ORDER)


def security_filters(
    keyword: str | None = Query(default=None, description="按巡视编号检索"),
    status: str | None = Query(default=None, description=STATUS_HINT),
    area: str | None = Query(default=None, description="按巡视区域检索"),
    operator: str | None = Query(default=None, description="按巡视人员检索"),
    handling: str | None = Query(default=None, description="按处理情况检索"),
    handover: str | None = Query(default=None, description="按交接事项检索"),
) -> dict[str, str | None]:
    """列表与异常统计共用的筛选参数：只收拢查询条件，不做业务判断。"""
    return {
        "keyword": keyword,
        "status": status,
        "area": area,
        "operator": operator,
        "handling": handling,
        "handover": handover,
    }


@router.get("", response_model=PageResult[dict])
def list_entries(
    filters: dict[str, str | None] = Depends(security_filters),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按统一口径过滤安防巡视列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(filters=filters, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/stats")
def stats(filters: dict[str, str | None] = Depends(security_filters)) -> list[dict[str, Any]]:
    """异常统计：与列表共用同一份筛选口径和数据来源。"""
    return service.summarize(filters=filters)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出安防巡视清单：返回全量数据，可见范围与原来一致。"""
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
    """对单条安防记录执行开始巡视、记录异常、完成巡视；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
