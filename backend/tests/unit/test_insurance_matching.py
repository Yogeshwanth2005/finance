from lib.insurance_matching import select_insurance_examples

ALL_PLANS = [
    {"id": "t1", "plan_type": "term", "sum_assured_max": 5000000},
    {"id": "t2", "plan_type": "term", "sum_assured_max": 10000000},
    {"id": "t3", "plan_type": "term", "sum_assured_max": 20000000},
    {"id": "h1", "plan_type": "health", "sum_assured_max": 500000},
    {"id": "h2", "plan_type": "health", "sum_assured_max": 1000000},
]


def test_filters_by_plan_type():
    result = select_insurance_examples("health", 500000, ALL_PLANS, count=5)
    assert [p["id"] for p in result] == ["h1", "h2"]


def test_sorts_by_closest_sum_assured_ascending_distance():
    result = select_insurance_examples("term", 9000000, ALL_PLANS, count=3)
    assert [p["id"] for p in result] == ["t2", "t1", "t3"]


def test_never_sorts_by_largest_or_cheapest_closest_only():
    result = select_insurance_examples("term", 4000000, ALL_PLANS, count=1)
    assert [p["id"] for p in result] == ["t1"]


def test_takes_only_first_count():
    result = select_insurance_examples("term", 9000000, ALL_PLANS, count=1)
    assert len(result) == 1


def test_defaults_count_to_config_value():
    many_term_plans = [{"id": f"t{i}", "plan_type": "term", "sum_assured_max": i * 1000000} for i in range(5)]
    assert len(select_insurance_examples("term", 5000000, many_term_plans)) == 2
