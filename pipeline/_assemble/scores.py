from datetime import date


def lookup_scores_at(bible: dict, target_date: date) -> dict:
    """Return {topic_id: score} using the last history entry <= target_date."""
    result = {}
    target_str = target_date.isoformat()
    for tid, entry in bible.items():
        if tid.startswith("_"):
            continue
        history = [h for h in entry.get("history", []) if h.get("date", "") <= target_str]
        result[tid] = history[-1]["score"] if history else 0.0
    return result
