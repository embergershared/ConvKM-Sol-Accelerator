from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class SelectedFilters(BaseModel):
    Topic: List[str]
    Sentiment: List[str]
    DateRange: List[str]


class ChartFilters(BaseModel):
    selected_filters: SelectedFilters


# ---------------------------------------------------------------------------
# Drill-down models (see plans/dashboard-drill-down.md, Stage B).
# All three drill endpoints accept the same `ChartFilters` payload as the
# dashboard so the drawer always reflects the global filter set.
# ---------------------------------------------------------------------------

DrillDimension = Literal["topic", "sentiment", "key_phrase"]
DrillBucket = Literal["day", "week"]


class DrillSelection(BaseModel):
    """A single drill selection — the chart element the user clicked."""

    dimension: DrillDimension
    value: str = Field(min_length=1, max_length=500)


class DrillTimeRange(BaseModel):
    """Inclusive lower bound, exclusive upper bound for the L2 call list."""

    from_: str = Field(alias="from")
    to: str

    model_config = {"populate_by_name": True}


class DrillTimeseriesRequest(BaseModel):
    selection: DrillSelection
    bucket: DrillBucket = "week"
    filters: Optional[ChartFilters] = None


class DrillCallsRequest(BaseModel):
    selection: DrillSelection
    time_range: Optional[DrillTimeRange] = None
    filters: Optional[ChartFilters] = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=25, ge=1, le=100)
