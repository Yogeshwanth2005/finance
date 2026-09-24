"""MongoDB access for the stored fund rows (spec section 5.2): the only module that touches the `fund_rows` collection.

Persistence must never break an API response, so every method logs its failure and returns; the store's in-memory rows stay
authoritative for the running process.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone

from pymongo import UpdateOne

from lib.finance_config import FUND_REPO_BATCH_SIZE
from lib.funds import WINDOWS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredFund:
    """One live Direct + Growth scheme: its identity, its newest NAV, its computed returns and its first NAV (spec section 4)."""

    scheme_code: str
    name: str
    fund_house: str
    category: str
    segment: str | None
    nav: float
    nav_date: date
    returns: dict[str, float | None]  # keys "1y" "3y" "5y" "max", percent; None where the fund has no value
    max_is_annualised: bool | None  # False for a fund under a year old, None while "max" is unknown
    computed_at: datetime  # timezone-aware UTC
    first_nav: float | None = None
    first_nav_date: date | None = None
    first_nav_source: str | None = None  # "checkpoint": found on a month-start snapshot; "first_seen": the earliest NAV we saw

    def to_doc(self) -> dict:
        return {
            "_id": self.scheme_code,
            "name": self.name,
            "fund_house": self.fund_house,
            "category": self.category,
            "segment": self.segment,
            "nav": self.nav,
            "nav_date": self.nav_date.isoformat(),
            "returns": dict(self.returns),
            "max_is_annualised": self.max_is_annualised,
            "first_nav": self.first_nav,
            "first_nav_date": self.first_nav_date.isoformat() if self.first_nav_date else None,
            "first_nav_source": self.first_nav_source,
            "computed_at": self.computed_at.isoformat(),
        }

    @classmethod
    def from_doc(cls, doc: dict) -> StoredFund:
        computed_at = datetime.fromisoformat(doc["computed_at"])
        first_nav_date = doc.get("first_nav_date")
        return cls(
            scheme_code=str(doc["_id"]),
            name=doc["name"],
            fund_house=doc["fund_house"],
            category=doc["category"],
            segment=doc.get("segment"),
            nav=float(doc["nav"]),
            nav_date=date.fromisoformat(doc["nav_date"]),
            returns={window: (doc.get("returns") or {}).get(window) for window in WINDOWS},
            max_is_annualised=doc.get("max_is_annualised"),
            computed_at=computed_at if computed_at.tzinfo else computed_at.replace(tzinfo=timezone.utc),
            first_nav=doc.get("first_nav"),
            first_nav_date=date.fromisoformat(first_nav_date) if first_nav_date else None,
            first_nav_source=doc.get("first_nav_source"),
        )


class MongoFundRepo:
    def __init__(self, collection):
        self._collection = collection

    async def load_all(self) -> list[StoredFund]:
        try:
            docs = await self._collection.find({}).to_list(length=None)
        except Exception:
            logger.exception("fund_rows: could not load the stored rows")
            return []
        funds = []
        for doc in docs:
            try:
                funds.append(StoredFund.from_doc(doc))
            except (KeyError, TypeError, ValueError):
                logger.warning("fund_rows: skipping an unreadable document (_id %s)", doc.get("_id"))
        return funds

    async def upsert_many(self, funds: list[StoredFund]) -> None:
        """Insert or overwrite every row, except that a stored first NAV is never overwritten: those fields are $setOnInsert."""
        operations = []
        for fund in funds:
            doc = fund.to_doc()
            first_nav_fields = {key: doc.pop(key) for key in ("first_nav", "first_nav_date", "first_nav_source")}
            del doc["_id"]
            operations.append(UpdateOne({"_id": fund.scheme_code}, {"$set": doc, "$setOnInsert": first_nav_fields}, upsert=True))
        await self._bulk_write(operations)

    async def set_first_nav(self, funds: list[StoredFund]) -> None:
        """Save first NAVs (and the Max return they give) for rows that have none yet; a row that already has one is left alone."""
        operations = [
            UpdateOne(
                {"_id": fund.scheme_code, "first_nav": None},
                {"$set": {
                    "first_nav": fund.first_nav,
                    "first_nav_date": fund.first_nav_date.isoformat() if fund.first_nav_date else None,
                    "first_nav_source": fund.first_nav_source,
                    "returns.max": fund.returns.get("max"),
                    "max_is_annualised": fund.max_is_annualised,
                }},
            )
            for fund in funds
        ]
        await self._bulk_write(operations)

    async def delete_missing(self, keep_codes: set[str]) -> None:
        """Delete every stored row whose scheme code is not in `keep_codes`. Never called with an empty set: that would wipe the collection."""
        if not keep_codes:
            return
        try:
            await self._collection.delete_many({"_id": {"$nin": sorted(keep_codes)}})
        except Exception:
            logger.exception("fund_rows: could not delete delisted rows")

    async def _bulk_write(self, operations: list[UpdateOne]) -> None:
        for start in range(0, len(operations), FUND_REPO_BATCH_SIZE):
            try:
                await self._collection.bulk_write(operations[start:start + FUND_REPO_BATCH_SIZE], ordered=False)
            except Exception:
                logger.exception("fund_rows: a bulk write failed")
