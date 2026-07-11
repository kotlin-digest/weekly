import sys
sys.path.insert(0, '.')

from pipeline.rollup import (
    natural_version_key,
    group_releases,
    rollup_id,
    collapse,
    apply_rollups,
    load_rollups,
)


# ── natural_version_key ───────────────────────────────────────────────────────

def test_natural_version_key_dev_number_ordering():
    assert natural_version_key("v1.12.10-alpha01+dev4443: Details") > \
           natural_version_key("v1.12.10-alpha01+dev4438: Details")


def test_natural_version_key_semver_double_digit():
    # 1.12.10 must sort ABOVE 1.12.9 (numeric, not lexicographic)
    assert natural_version_key("1.12.10") > natural_version_key("1.12.9")


def test_natural_version_key_empty_title():
    assert natural_version_key("") == ()


# ── group_releases ────────────────────────────────────────────────────────────

def _cm(id, date, title, topics=("compose-multiplatform",)):
    return {"id": id, "source_id": "cm", "date": date, "title": title,
            "topics": list(topics) if topics else topics, "summary": "s"}


def test_group_releases_keeps_newest_per_source():
    stm = {"cm": "changelog", "blog1": "blog"}
    arts = [
        _cm("a", "2026-07-08", "v1.0+dev10"),
        _cm("b", "2026-07-10", "v1.0+dev20"),
        _cm("c", "2026-07-09", "v1.0+dev15"),
    ]
    groups = group_releases(arts, stm)
    assert len(groups) == 1
    g = groups[0]
    assert g["survivor"]["id"] == "b"
    assert {c["id"] for c in g["collapsed"]} == {"a", "c"}


def test_group_releases_same_day_tiebreak_by_version():
    stm = {"cm": "changelog"}
    arts = [
        _cm("a", "2026-07-10", "v1.0+dev4438"),
        _cm("b", "2026-07-10", "v1.0+dev4443"),
    ]
    g = group_releases(arts, stm)[0]
    assert g["survivor"]["id"] == "b"  # dev4443 > dev4438 on the same day


def test_group_releases_ignores_non_changelog():
    stm = {"blog1": "blog"}
    arts = [{"id": "a", "source_id": "blog1", "date": "2026-07-10",
             "title": "Post", "topics": ["compose"], "summary": "s"}]
    assert group_releases(arts, stm) == []


def test_group_releases_excludes_unsummarized_from_survivor():
    # The unsummarized (topics=None) build has the HIGHER version but must not win.
    stm = {"cm": "changelog"}
    arts = [
        _cm("new", "2026-07-10", "v1.0+dev4447", topics=None),
        _cm("ok",  "2026-07-10", "v1.0+dev4443"),
    ]
    groups = group_releases(arts, stm)
    assert len(groups) == 1
    assert groups[0]["survivor"]["id"] == "ok"
    assert groups[0]["collapsed"] == []


def test_group_releases_singleton_no_collapse():
    stm = {"cm": "changelog"}
    arts = [_cm("a", "2026-07-10", "v1.0")]
    g = group_releases(arts, stm)[0]
    assert g["collapsed"] == []


# ── rollup_id ─────────────────────────────────────────────────────────────────

def test_rollup_id_order_independent():
    assert rollup_id(["a", "b", "c"]) == rollup_id(["c", "a", "b"])


def test_rollup_id_set_sensitive():
    assert rollup_id(["a", "b"]) != rollup_id(["a", "b", "c"])


# ── collapse ──────────────────────────────────────────────────────────────────

def test_collapse_passes_through_non_changelog_and_attaches_builds():
    stm = {"cm": "changelog", "blog1": "blog"}
    arts = [
        {"id": "p", "source_id": "blog1", "date": "2026-07-10",
         "title": "Post", "topics": ["compose"], "summary": "s"},
        _cm("a", "2026-07-08", "v1.0+dev10"),
        _cm("b", "2026-07-10", "v1.0+dev20"),
    ]
    kept, rollups = collapse(arts, stm)
    assert {a["id"] for a in kept} == {"p", "b"}
    surv = next(a for a in kept if a["id"] == "b")
    assert len(surv["collapsed_builds"]) == 1
    assert surv["collapsed_builds"][0]["title"] == "v1.0+dev10"
    assert "rollup_id" in surv
    assert len(rollups) == 1
    assert rollups[0]["rollup_id"] == surv["rollup_id"]
    # queue entry carries survivor + folded builds with their summaries
    assert rollups[0]["survivor"]["title"] == "v1.0+dev20"
    assert rollups[0]["builds"][0]["summary"] == "s"


def test_collapse_singleton_no_rollup_no_builds():
    stm = {"cm": "changelog"}
    arts = [_cm("a", "2026-07-10", "v1.0")]
    kept, rollups = collapse(arts, stm)
    assert rollups == []
    assert "collapsed_builds" not in kept[0]


# ── apply / load ──────────────────────────────────────────────────────────────

def test_load_rollups_missing_file_returns_empty(tmp_path):
    assert load_rollups(path=tmp_path / "nope.json") == {}


def test_apply_rollups_writes_and_updates(tmp_path):
    p = tmp_path / "rollups.json"
    apply_rollups([{"rollup_id": "r1", "summary": "S1", "source_id": "cm"}], path=p)
    assert load_rollups(path=p)["r1"]["summary"] == "S1"
    # re-apply overwrites in place, keyed by rollup_id
    apply_rollups([{"rollup_id": "r1", "summary": "S1b", "source_id": "cm"}], path=p)
    data = load_rollups(path=p)
    assert data["r1"]["summary"] == "S1b"
    assert data["r1"]["source_id"] == "cm"
