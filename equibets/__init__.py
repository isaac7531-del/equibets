"""Utilities for eventing results data sources."""

from .results import EventingResult, consolidate_results, predict_finishing_score
from .sources import EventSource, load_event_sources, sources_for_region


def current_event_window(*args, **kwargs):
    """Return the rolling FEI current-event search window."""

    from .fei_bot import current_event_window as build_current_event_window

    return build_current_event_window(*args, **kwargs)

__all__ = [
    "EventSource",
    "EventingResult",
    "consolidate_results",
    "current_event_window",
    "load_event_sources",
    "predict_finishing_score",
    "sources_for_region",
]
