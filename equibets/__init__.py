"""Utilities for eventing results data sources."""

from importlib import import_module

__all__ = [
    "EventSource",
    "EventingResult",
    "LiveEventScore",
    "consolidate_live_scores",
    "consolidate_results",
    "load_event_sources",
    "merge_completed_live_results",
    "predict_finishing_score",
    "pull_current_event_scores",
    "pull_startbox_current_event_scores",
    "rank_live_scores",
    "search_live_scores",
    "sources_for_region",
]

_EXPORT_MODULES = {
    "EventSource": "sources",
    "EventingResult": "results",
    "LiveEventScore": "live_scoring",
    "consolidate_live_scores": "live_scoring",
    "consolidate_results": "results",
    "load_event_sources": "sources",
    "merge_completed_live_results": "live_scoring",
    "predict_finishing_score": "results",
    "pull_current_event_scores": "live_scoring",
    "pull_startbox_current_event_scores": "live_scoring",
    "rank_live_scores": "live_scoring",
    "search_live_scores": "live_scoring",
    "sources_for_region": "sources",
}


def __getattr__(name: str):
    if name not in _EXPORT_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(f".{_EXPORT_MODULES[name]}", __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
