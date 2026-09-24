"""StoredFund documents and MongoFundRepo, against a fake collection that records what it is asked to do (spec sections 4, 5.2)."""

import logging
from datetime import date

import pytest
from pymongo import UpdateOne

from lib import fund_repo
from lib.fund_repo import MongoFundRepo, StoredFund

from .stored_fund_fixtures import NOW, stored, unresolved


class FakeCursor:
    def __init__(self, docs, fail):
        self._docs = docs
        self._fail = fail

    async def to_list(self, length=None):
        if self._fail:
            raise RuntimeError("mongo is down")
        return list(self._docs)


class FakeCollection:
    def __init__(self, docs=(), fail=False):
        self.docs = list(docs)
        self.fail = fail
        self.bulk_attempts = []  # (operations, ordered) of every bulk_write call, failed or not
        self.deletes = []

    def find(self, query):
        assert query == {}
        return FakeCursor(self.docs, self.fail)

    async def bulk_write(self, operations, ordered):
        self.bulk_attempts.append((operations, ordered))
        if self.fail:
            raise RuntimeError("mongo is down")

    async def delete_many(self, query):
        self.deletes.append(query)
        if self.fail:
            raise RuntimeError("mongo is down")


def test_a_document_has_exactly_the_fields_of_the_spec_and_string_dates():
    doc = stored("148921").to_doc()
    assert set(doc) == {
        "_id", "name", "fund_house", "category", "segment", "nav", "nav_date", "returns", "max_is_annualised",
        "first_nav", "first_nav_date", "first_nav_source", "computed_at",
    }
    assert doc["_id"] == "148921"
    assert doc["nav_date"] == "2026-09-23" and doc["first_nav_date"] == "2013-01-01"
    assert doc["computed_at"] == "2026-09-24T09:00:00+00:00"


@pytest.mark.parametrize("fund", [stored("1"), unresolved("2"), stored("3", segment=None, category="Debt ETF")])
def test_a_fund_survives_a_round_trip_through_its_document(fund):
    assert StoredFund.from_doc(fund.to_doc()) == fund


def test_a_stored_time_without_a_zone_is_read_as_utc():
    doc = stored("1").to_doc()
    doc["computed_at"] = "2026-09-24T09:00:00"
    assert StoredFund.from_doc(doc).computed_at == NOW


def test_missing_return_keys_read_as_none():
    doc = stored("1").to_doc()
    doc["returns"] = {"1y": 5.0}
    assert StoredFund.from_doc(doc).returns == {"1y": 5.0, "3y": None, "5y": None, "max": None}


async def test_load_all_returns_the_stored_funds():
    repo = MongoFundRepo(FakeCollection([stored("1").to_doc(), unresolved("2").to_doc()]))
    assert [fund.scheme_code for fund in await repo.load_all()] == ["1", "2"]


async def test_load_all_skips_an_unreadable_document_and_keeps_the_rest(caplog):
    broken = stored("2").to_doc()
    del broken["nav_date"]
    repo = MongoFundRepo(FakeCollection([stored("1").to_doc(), broken, {"_id": "3", "nav_date": "not a date"}]))
    with caplog.at_level(logging.WARNING):
        assert [fund.scheme_code for fund in await repo.load_all()] == ["1"]
    assert "unreadable" in caplog.text


async def test_load_all_returns_nothing_and_never_raises_when_mongo_is_down():
    assert await MongoFundRepo(FakeCollection([stored("1").to_doc()], fail=True)).load_all() == []


async def test_upsert_many_sets_everything_but_the_first_nav_fields_which_are_set_on_insert():
    collection = FakeCollection()
    await MongoFundRepo(collection).upsert_many([stored("1")])
    [(operations, ordered)] = collection.bulk_attempts
    [operation] = operations
    assert ordered is False
    assert isinstance(operation, UpdateOne) and operation._upsert is True
    assert operation._filter == {"_id": "1"}
    assert set(operation._doc["$setOnInsert"]) == {"first_nav", "first_nav_date", "first_nav_source"}
    assert operation._doc["$setOnInsert"]["first_nav"] == 10.0
    assert set(operation._doc["$set"]).isdisjoint(operation._doc["$setOnInsert"])
    assert "_id" not in operation._doc["$set"]
    assert operation._doc["$set"]["returns"] == {"1y": 12.0, "3y": 12.0, "5y": 12.0, "max": 12.0}
    assert operation._doc["$set"]["nav_date"] == "2026-09-23"


async def test_upsert_many_writes_in_batches(monkeypatch):
    monkeypatch.setattr(fund_repo, "FUND_REPO_BATCH_SIZE", 2)
    collection = FakeCollection()
    await MongoFundRepo(collection).upsert_many([stored(str(i)) for i in range(5)])
    assert [len(operations) for operations, _ in collection.bulk_attempts] == [2, 2, 1]


async def test_upsert_many_of_nothing_writes_nothing():
    collection = FakeCollection()
    await MongoFundRepo(collection).upsert_many([])
    assert collection.bulk_attempts == []


async def test_set_first_nav_only_touches_a_row_that_has_no_first_nav_yet():
    collection = FakeCollection()
    fund = stored("1", first_nav=10.0, first_nav_date=date(2013, 3, 1), first_nav_source="checkpoint")
    await MongoFundRepo(collection).set_first_nav([fund])
    [operation] = collection.bulk_attempts[0][0]
    assert operation._filter == {"_id": "1", "first_nav": None}
    assert not operation._upsert
    assert operation._doc == {"$set": {
        "first_nav": 10.0, "first_nav_date": "2013-03-01", "first_nav_source": "checkpoint", "returns.max": 12.0, "max_is_annualised": True,
    }}


async def test_delete_missing_deletes_everything_outside_the_kept_codes():
    collection = FakeCollection()
    await MongoFundRepo(collection).delete_missing({"2", "1"})
    assert collection.deletes == [{"_id": {"$nin": ["1", "2"]}}]


async def test_delete_missing_never_runs_with_an_empty_set():
    collection = FakeCollection()
    await MongoFundRepo(collection).delete_missing(set())
    assert collection.deletes == []


async def test_writes_never_raise_when_mongo_is_down_and_a_failed_batch_does_not_stop_the_next(monkeypatch):
    monkeypatch.setattr(fund_repo, "FUND_REPO_BATCH_SIZE", 2)
    collection = FakeCollection(fail=True)
    repo = MongoFundRepo(collection)
    await repo.upsert_many([stored(str(i)) for i in range(3)])
    await repo.set_first_nav([stored("1")])
    await repo.delete_missing({"1"})
    assert len(collection.bulk_attempts) == 3  # two batches of the upsert, one set_first_nav
    assert len(collection.deletes) == 1
