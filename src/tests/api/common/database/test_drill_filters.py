"""Tests for the SQL fragment helpers used by drill_routes.

The DB-touching async functions need a live SQL Server (or pyodbc) to
exercise meaningfully, so we focus on the pure builders that translate
ChartFilters + DrillSelection into parameterised WHERE fragments.
"""

import pytest

from api.models.input_models import (
    ChartFilters,
    DrillSelection,
    SelectedFilters,
)
from common.database.sqldb_service import (
    _DRILL_DATE_RANGE_DAYS,
    _build_drill_filter_clauses,
    _build_drill_selection_clause,
    _drill_from_clause,
)


pytestmark = pytest.mark.unittest


# ---------------------------------------------------------------------------
# _build_drill_selection_clause
# ---------------------------------------------------------------------------

def test_selection_topic_targets_mined_topic():
    sql, params = _build_drill_selection_clause("topic", "Billing")
    assert "pd.mined_topic = ?" == sql
    assert params == ["Billing"]


def test_selection_sentiment():
    sql, params = _build_drill_selection_clause("sentiment", "Negative")
    assert "pd.sentiment = ?" == sql
    assert params == ["Negative"]


def test_selection_key_phrase_targets_join_alias():
    sql, params = _build_drill_selection_clause("key_phrase", "lost phone")
    assert "kp.key_phrase = ?" == sql
    assert params == ["lost phone"]


def test_selection_unsupported_raises():
    with pytest.raises(ValueError):
        _build_drill_selection_clause("not_a_dimension", "x")


# ---------------------------------------------------------------------------
# _drill_from_clause
# ---------------------------------------------------------------------------

def test_from_clause_topic_no_join():
    from_sql = _drill_from_clause("topic")
    assert "processed_data" in from_sql
    assert "JOIN" not in from_sql


def test_from_clause_key_phrase_joins():
    from_sql = _drill_from_clause("key_phrase")
    assert "processed_data_key_phrases" in from_sql
    assert "INNER JOIN" in from_sql


# ---------------------------------------------------------------------------
# _build_drill_filter_clauses
# ---------------------------------------------------------------------------

def _filters(topic=None, sentiment=None, date_range=None, satisfaction=None):
    """Build a ChartFilters payload — adds Satisfaction via raw dict because
    the existing SelectedFilters Pydantic model doesn't expose that field."""
    payload = {
        "Topic": topic or [],
        "Sentiment": sentiment or [],
        "DateRange": date_range or [],
    }
    cf = ChartFilters(selected_filters=SelectedFilters(**payload))
    # Inject Satisfaction post-hoc (the legacy builder accepts it).
    cf.selected_filters = SelectedFilters(**payload)
    return cf


def test_filter_topic_in_list_params_bound():
    clauses, params = _build_drill_filter_clauses(
        _filters(topic=["Billing", "Lost or Stolen Devices"])
    )
    assert clauses == ["pd.mined_topic IN (?, ?)"]
    assert params == ["Billing", "Lost or Stolen Devices"]


def test_filter_sentiment_skips_all_sentinel():
    clauses, params = _build_drill_filter_clauses(
        _filters(sentiment=["all"])
    )
    assert clauses == []
    assert params == []


def test_filter_date_range_known_window():
    clauses, params = _build_drill_filter_clauses(
        _filters(date_range=["Last 7 days"])
    )
    assert clauses == [
        "CAST(pd.StartTime AS DATETIME) >= DATEADD(day, -?, GETDATE())"
    ]
    assert params == [_DRILL_DATE_RANGE_DAYS["Last 7 days"]]


def test_filter_year_to_date_no_bound_param():
    clauses, params = _build_drill_filter_clauses(
        _filters(date_range=["Year to Date"])
    )
    assert clauses == [
        "CAST(pd.StartTime AS DATETIME) >= DATEFROMPARTS(YEAR(GETDATE()), 1, 1)"
    ]
    assert params == []


def test_filter_combined():
    clauses, params = _build_drill_filter_clauses(
        _filters(topic=["Billing"], sentiment=["Negative"], date_range=["Last 7 days"])
    )
    # Each clause appears once; params concatenated in deterministic order.
    assert "pd.mined_topic IN (?)" in clauses
    assert "pd.sentiment IN (?)" in clauses
    assert any("DATEADD" in c for c in clauses)
    assert params == ["Billing", "Negative", 7]


def test_filter_none_yields_empty():
    clauses, params = _build_drill_filter_clauses(None)
    assert clauses == []
    assert params == []


def test_drill_selection_pydantic_validates():
    sel = DrillSelection(dimension="topic", value="Billing")
    assert sel.dimension == "topic"
    assert sel.value == "Billing"
