from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Segment = Literal["nifty", "large", "mid", "small"]


class FundRow(BaseModel):
    scheme_code: str
    name: str
    fund_house: str
    category: str  # AMFI's own sub-category label, e.g. "Large Cap Fund"
    segment: Segment | None  # None for every category outside the four equity segments
    nav: float
    nav_date: date
    start_date: date | None  # the fund's first NAV on record; None until the first-NAV pass reaches it
    returns: dict[str, float | None]  # percent, keys "1y" "3y" "5y" "max"; None where the fund has no value for the window
    max_is_annualised: bool | None  # False for a fund under a year old ("max" is then its absolute return); None while "max" is unknown


Status = Literal["warming", "ready", "stale", "unavailable"]
Window = Literal["1y", "3y", "5y", "max"]


class SegmentLists(BaseModel):
    nifty: list[FundRow] = Field(default_factory=list)
    large: list[FundRow] = Field(default_factory=list)
    mid: list[FundRow] = Field(default_factory=list)
    small: list[FundRow] = Field(default_factory=list)


class FundSectionResponse(BaseModel):
    key: str  # a segment name, or "cat-" plus the category label as a slug
    title: str
    funds: list[FundRow]


class FundsTopResponse(BaseModel):
    status: Status
    as_of: date | None  # newest NAV date across the stored rows; None until the first fill finishes
    window: Window
    max_pending: bool  # True while some fund's first NAV is unknown, so its Max return is still missing
    segments: SegmentLists


class FundsSearchResponse(BaseModel):
    status: Status
    as_of: date | None
    window: Window
    max_pending: bool
    query: str
    fund_houses: list[str]  # every fund house the query matched
    sections: list[FundSectionResponse]
