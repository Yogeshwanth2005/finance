"""The allocation inputs on ProfileInput: risk tolerance and investment horizon."""

import pytest
from pydantic import ValidationError

from models.profile import FamilyProfile, ProfileInput

from .profiles import payload


def test_profiles_saved_before_the_fields_existed_get_moderate_and_ten_years():
    # Mongo holds profiles without these keys; _response() re-validates them through ProfileInput on every read.
    profile = ProfileInput(**payload())
    assert profile.risk_tolerance == "moderate"
    assert profile.investment_horizon_years == 10


@pytest.mark.parametrize("risk", ["conservative", "moderate", "aggressive"])
def test_accepts_each_risk_tolerance(risk):
    assert ProfileInput(**payload(risk_tolerance=risk)).risk_tolerance == risk


@pytest.mark.parametrize("risk", ["reckless", "Moderate", ""])
def test_rejects_an_unknown_risk_tolerance(risk):
    with pytest.raises(ValidationError, match="risk_tolerance"):
        ProfileInput(**payload(risk_tolerance=risk))


@pytest.mark.parametrize("years", [0, -3])
def test_investment_horizon_must_be_at_least_one_year(years):
    with pytest.raises(ValidationError, match="investment_horizon_years"):
        ProfileInput(**payload(investment_horizon_years=years))


def test_investment_horizon_accepts_one_year():
    assert ProfileInput(**payload(investment_horizon_years=1)).investment_horizon_years == 1


def test_investment_horizon_is_capped_at_sixty_years():
    assert ProfileInput(**payload(investment_horizon_years=60)).investment_horizon_years == 60
    with pytest.raises(ValidationError, match="investment_horizon_years"):
        ProfileInput(**payload(investment_horizon_years=61))


def test_family_profile_keeps_the_new_fields_for_persistence():
    stored = FamilyProfile(id="user-1", **payload(risk_tolerance="aggressive", investment_horizon_years=3)).model_dump()
    assert stored["risk_tolerance"] == "aggressive"
    assert stored["investment_horizon_years"] == 3
