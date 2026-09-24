from fastapi import APIRouter, Depends, HTTPException, Query, Request

from lib.auth import get_current_user
from lib.fund_repo import StoredFund
from lib.fund_store import FundStore
from models.funds import FundRow, FundSectionResponse, FundsSearchResponse, FundsTopResponse, SegmentLists, Window

router = APIRouter(prefix="/funds", tags=["funds"], dependencies=[Depends(get_current_user)])


def get_fund_store(request: Request) -> FundStore:
    return request.app.state.funds


def to_row(fund: StoredFund) -> FundRow:
    return FundRow(
        scheme_code=fund.scheme_code,
        name=fund.name,
        fund_house=fund.fund_house,
        category=fund.category,
        segment=fund.segment,
        nav=fund.nav,
        nav_date=fund.nav_date,
        start_date=fund.first_nav_date,
        returns=fund.returns,
        max_is_annualised=fund.max_is_annualised,
    )


@router.get("/top", response_model=FundsTopResponse)
async def top_funds(window: Window = "3y", store: FundStore = Depends(get_fund_store)) -> FundsTopResponse:
    store.ensure_fresh()
    return FundsTopResponse(
        status=store.status,
        as_of=store.as_of,
        window=window,
        max_pending=store.max_pending,
        segments=SegmentLists(**{segment: [to_row(fund) for fund in funds] for segment, funds in store.top(window).items()}),
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
    fund_houses, sections = store.search(query, window)
    return FundsSearchResponse(
        status=store.status,
        as_of=store.as_of,
        window=window,
        max_pending=store.max_pending,
        query=query,
        fund_houses=fund_houses,
        sections=[FundSectionResponse(key=section.key, title=section.title, funds=[to_row(fund) for fund in section.funds]) for section in sections],
    )
