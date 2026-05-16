"""Utilities for eventing results data sources."""

from importlib import import_module
from typing import TYPE_CHECKING

from .results import EventingResult, consolidate_results, predict_finishing_score
from .sources import EventSource, load_event_sources, sources_for_region

if TYPE_CHECKING:
    from .live_scoring import CurrentEvent, parse_startbox_calendar, refresh_startbox_feed

_LIVE_SCORING_EXPORTS = {
    "CurrentEvent",
    "parse_startbox_calendar",
    "refresh_startbox_feed",
}

__all__ = [
    "CurrentEvent",
    "EventSource",
    "EventingResult",
    "consolidate_results",
    "load_event_sources",
    "parse_startbox_calendar",
    "predict_finishing_score",
    "refresh_startbox_feed",
    "sources_for_region",
]


def __getattr__(name: str):
    if name in _LIVE_SCORING_EXPORTS:
        live_scoring = import_module(".live_scoring", __name__)
        return getattr(live_scoring, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
