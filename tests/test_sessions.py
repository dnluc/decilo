"""Tests del registro de sesiones y sus transiciones (sin modelos de IA)."""

import pytest
from fastapi.testclient import TestClient

from decilo.app import app, registry
from decilo.models import Session
from decilo.sessions import InvalidTransition, SessionNotFound, SessionRegistry


def make_session(id_: str = "s1", **overrides) -> Session:
    defaults = dict(id=id_, title="Charla", source_language="en", translation_languages=["es"], status="starting")
    defaults.update(overrides)
    return Session(**defaults)


def test_register_and_get():
    reg = SessionRegistry()
    reg.register(make_session())
    assert reg.get("s1").session.id == "s1"


def test_get_missing_raises():
    reg = SessionRegistry()
    with pytest.raises(SessionNotFound):
        reg.get("no-existe")


def test_register_duplicate_raises():
    reg = SessionRegistry()
    reg.register(make_session())
    with pytest.raises(ValueError):
        reg.register(make_session())


@pytest.mark.parametrize(
    "start,target,allowed",
    [
        ("starting", "live", True),
        ("starting", "degraded", True),
        ("starting", "error", True),
        ("starting", "ended", True),
        ("live", "degraded", True),
        ("live", "live", True),
        ("degraded", "live", True),
        ("live", "starting", False),
        ("error", "starting", True),
        ("error", "ended", True),
        ("error", "error", False),
        ("error", "live", False),
        ("ended", "starting", False),
        ("ended", "live", False),
    ],
)
def test_transitions(start, target, allowed):
    reg = SessionRegistry()
    record = reg.register(make_session(status=start))
    if allowed:
        record.transition_to(target)
        assert record.session.status == target
    else:
        with pytest.raises(InvalidTransition):
            record.transition_to(target)


def test_catalog_empty():
    registry._records.clear()
    client = TestClient(app)
    resp = client.get("/api/v1/sessions")
    assert resp.status_code == 200
    assert resp.json() == {"sessions": []}


def test_catalog_two_sessions_independent():
    registry._records.clear()
    registry.register(make_session("a", status="live"))
    registry.register(make_session("b", status="live", title="Otra charla"))
    client = TestClient(app)
    resp = client.get("/api/v1/sessions")
    ids = {s["id"] for s in resp.json()["sessions"]}
    assert ids == {"a", "b"}

    detail_a = client.get("/api/v1/sessions/a").json()
    assert detail_a["id"] == "a"
    assert detail_a["title"] != "Otra charla"


def test_session_detail_404():
    registry._records.clear()
    client = TestClient(app)
    resp = client.get("/api/v1/sessions/no-existe")
    assert resp.status_code == 404


def test_stream_status_is_shared_with_http_and_validated():
    from decilo.app import _gateway_for, gateways
    registry._records.clear()
    gateways.clear()
    registry.register(make_session("status-test", status="live"))
    stream = _gateway_for("status-test").stream
    stream.record_status(stream.session.model_copy(update={"status": "ended"}))
    client = TestClient(app)
    assert client.get("/api/v1/sessions/status-test").json()["status"] == "ended"
    assert client.get("/api/v1/sessions").json()["sessions"][0]["status"] == "ended"
    assert stream.snapshot().data.session.status == "ended"
    with pytest.raises(InvalidTransition):
        stream.record_status(stream.session.model_copy(update={"status": "live"}))
    assert stream.seq == 1
    assert stream.session.status == "ended"
    registry._records.clear()
    gateways.clear()
