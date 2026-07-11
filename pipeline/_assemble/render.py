import json
from datetime import date, datetime

SPARK_CHARS = "▁▂▃▄▅▆▇█"
DATA_MARKER = "// @@DIGEST_DATA@@"
OFFICIAL_SOURCE_IDS = {"kotlin-blog", "android-developers-blog", "android-developers-medium", "jetbrains-blog"}


def spark_from_history(history: list, n: int = 7) -> str:
    """Map last n history scores to spark bar characters."""
    entries = history[-n:]
    if not entries:
        return ""
    scores = [e.get("score", 0.0) for e in entries]
    max_s = max(scores) or 1.0
    return "".join(SPARK_CHARS[min(7, int(s / max_s * 8))] for s in scores)


def inject_data(template: str, data_block: str) -> str:
    """Replace @@DIGEST_DATA@@ marker in template with generated data block."""
    if DATA_MARKER not in template:
        raise ValueError("DATA_MARKER not found in template — was template.html created?")
    return template.replace(DATA_MARKER, data_block)


def _stype(source_id: str, source_type: str) -> str:
    if source_id in OFFICIAL_SOURCE_IDS:
        return "official"
    if source_type == "changelog":
        return "changelog"
    if source_type == "discussion":
        return "discussion"
    return "community"


def _js_str(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")


def build_data_block(
    edition: str,
    start: date,
    end: date,
    chapters: list,
    bible: dict,
    source_type_map: dict,
    clusters: list,
) -> str:
    lines = ["// ══ DATA ════════════════════════════════════════════════════════════════════", ""]

    # TOPICS — one entry per cluster (for the filter UI)
    topics_js = ",\n  ".join(
        "{{ id:{}, label:{} }}".format(json.dumps(c["id"]), json.dumps(c["label"]))
        for c in clusters
    )
    lines.append("const TOPICS = [\n  {}\n];".format(topics_js))
    lines.append("")

    # TRENDING_DATA — top 10 non-meta topics by current score
    trending = sorted(
        [(tid, entry) for tid, entry in bible.items() if not tid.startswith("_")],
        key=lambda x: x[1].get("score", 0.0),
        reverse=True,
    )[:20]
    trending_items = []
    for tid, entry in trending:
        sp = spark_from_history(entry.get("history", []))
        score = int(entry.get("score", 0.0))
        trending_items.append(
            "  {{ name:{}, score:{}, spark:{} }}".format(json.dumps(tid), score, json.dumps(sp))
        )
    lines.append("const TRENDING_DATA = [\n" + ",\n".join(trending_items) + "\n];")
    lines.append("")

    # CHAPTERS
    week_start_str = start.isoformat()
    chapter_blocks = []
    for ch in chapters:
        # use first article's top topic history as chapter spark proxy
        spark = ""
        for a in ch["articles"]:
            for tid in a.get("topics", []):
                if tid in bible:
                    spark = spark_from_history(bible[tid].get("history", []))
                    break
            if spark:
                break

        article_blocks = []
        for a in ch["articles"]:
            is_new = a.get("date", "") >= week_start_str
            src_id = a.get("source_id", "")
            src_type = source_type_map.get(src_id, "blog")
            stype = _stype(src_id, src_type)

            try:
                d = datetime.strptime(a["date"], "%Y-%m-%d")
                date_str = d.strftime("%-d %b")
            except Exception:
                date_str = a.get("date", "")

            summary = a.get("summary") or ""
            snap_js = "null"
            if a.get("code_snippet"):
                snap_js = "{{ label:{}, code:{} }}".format(
                    json.dumps(a.get("snippet_label", "")),
                    json.dumps(a.get("code_snippet", "")),
                )

            topics_js = json.dumps(a.get("topics", []))
            source_name = src_id.replace("-", " ").title()

            article_blocks.append(
                "      {{ id:{}, col:{},\n"
                "        title:{},\n"
                "        url:{}, source:{}, stype:{}, date:{}, isNew:{},\n"
                "        topics:{},\n"
                "        summary:{},\n"
                "        snap:{}\n"
                "      }}".format(
                    json.dumps(a["id"]), json.dumps(a["col"]),
                    json.dumps(a["title"]),
                    json.dumps(a["url"]), json.dumps(source_name),
                    json.dumps(stype), json.dumps(date_str),
                    "true" if is_new else "false",
                    topics_js,
                    json.dumps(summary),
                    snap_js,
                )
            )

        score_int = int(ch["score"])
        chapter_blocks.append(
            "  {{\n"
            "    id:{}, title:{},\n"
            "    topics:[{}], score:{}, spark:{},\n"
            "    articles:[\n"
            "{}\n"
            "    ]\n"
            "  }}".format(
                json.dumps(ch["id"]), json.dumps(ch["label"]),
                json.dumps(ch["id"]), score_int, json.dumps(spark),
                ",\n".join(article_blocks),
            )
        )

    lines.append("const CHAPTERS = [\n" + ",\n".join(chapter_blocks) + "\n];")
    lines.append("")
    return "\n".join(lines)
