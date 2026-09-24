from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Segment = Literal["nifty", "large", "mid", "small"]


class FundRow(BaseModel):
    scheme_code: str
    name: str
    fund_house: str
    segment: Segment
    nav: float
    nav_date: date
    start_date: date  # first NAV on record: for a Direct plan that is never earlier than January 2013
    returns: dict[str, float | None]  # percent, keys "1y" "3y" "5y" "max"; None when the fund has too little history
    max_is_annualised: bool  # False for a fund under a year old: "max" is then its absolute return


Status = Literal["warming", "ready", "stale", "unavailable"]
Window = Literal["1y", "3y", "5y", "max"]


class SegmentLists(BaseModel):
    nifty: list[FundRow] = Field(default_factory=list)
    large: list[FundRow] = Field(default_factory=list)
    mid: list[FundRow] = Field(default_factory=list)
    small: list[FundRow] = Field(default_factory=list)


class FundsTopResponse(BaseModel):
    status: Status
    as_of: date | None  # newest NAV date in the cache; None until the first load finishes
    window: Window
    failed_count: int  # catalog funds left out because their NAV history could not be fetched or was unusable
    segments: SegmentLists


class FundsSearchResponse(BaseModel):
    status: Status
    as_of: date | None
    window: Window
    failed_count: int
    query: str
    fund_houses: list[str]  # every fund house the query matched
    groups: SegmentLists
