from fastapi import APIRouter, Depends, HTTPException, Query, Request

from lib.auth import get_current_user
from lib.funds import FundStore
from models.funds import FundsSearchResponse, FundsTopResponse, SegmentLists, Window

router = APIRouter(prefix="/funds", tags=["funds"], dependencies=[Depends(get_current_user)])


def get_fund_store(request: Request) -> FundStore:
    return request.app.state.funds


@router.get("/top", response_model=FundsTopResponse)
async def top_funds(window: Window = "3y", store: FundStore = Depends(get_fund_store)) -> FundsTopResponse:
    store.ensure_fresh()
    return FundsTopResponse(
        status=store.status,
        as_of=store.as_of,
        window=window,
        failed_count=store.failed_count,
        segments=SegmentLists(**store.top(window)),
    )


@router.get("/search", response_model=FundsSearchResponse)
async def search_funds(
    q: str = Query(min_length=2, max_length=60),
    window: Window = "3y",
    store: FundStore = Depends(get_fund_store),
) -> FundsSearchResponse:
    query = q.strip()
    if len(query) < 2:  # "  " passes the length check above but would otherwise match every fund house
        raise HTTPException(status_code=422, detail="Enter at least 2 characters")
    store.ensure_fresh()
    fund_houses, groups = store.search(query, window)
    return FundsSearchResponse(
        status=store.status,
        as_of=store.as_of,
        window=window,
        failed_count=store.failed_count,
        query=query,
        fund_houses=fund_houses,
        groups=SegmentLists(**groups),
    )
