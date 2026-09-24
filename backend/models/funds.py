from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

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
