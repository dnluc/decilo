"""Tests de los modelos del contrato (sin modelos de IA, corren en CI)."""

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from decilo.models import (
    CaptionData, Event, GapData, Session, SessionCatalog, SessionSnapshotEvent,
)


def test_session_valid():
    s = Session(id="s1", title="Charla", source_language="en", translation_languages=["es"], status="live")
    assert s.status == "live"


def test_session_rejects_translation_language_equal_to_original():
    with pytest.raises((ValidationError, ValueError)):
        Session(id="s1", title="Charla", source_language="en", translation_languages=["en"], status="live")


def test_session_rejects_invalid_language():
    with pytest.raises(ValidationError):
        Session(id="s1", title="Charla", source_language="fr", status="live")


def test_caption_rejects_empty_text():
    with pytest.raises(ValidationError):
        CaptionData(
            segment_id="seg-1", segment_seq=1, kind="transcript", language="en",
            revision=1, text="", status="final", start_ms=0, end_ms=100,
        )


def test_caption_rejects_end_before_start():
    with pytest.raises((ValidationError, ValueError)):
        CaptionData(
            segment_id="seg-1", segment_seq=1, kind="transcript", language="en",
            revision=1, text="hola", status="final", start_ms=500, end_ms=100,
        )


def test_translation_requires_source_revision():
    with pytest.raises((ValidationError, ValueError)):
        CaptionData(
            segment_id="seg-1", segment_seq=1, kind="translation", language="es",
            revision=1, text="hola", status="final", start_ms=0, end_ms=100,
        )


def test_translation_with_source_revision_is_valid():
    c = CaptionData(
        segment_id="seg-1", segment_seq=1, kind="translation", language="es",
        revision=1, source_revision=2, text="hola", status="final", start_ms=0, end_ms=100,
    )
    assert c.source_revision == 2


# Regression cases from Codex's review of PR #3. Exercise JSON input as well
# as Python construction, since events/fixtures cross the browser boundary.
@pytest.mark.parametrize("text", ["a" * 8192, "á" * 4096, "🙂" * 2048])
def test_caption_accepts_utf8_byte_limit_without_changing_text(text):
    c = CaptionData(
        segment_id="seg-1", segment_seq=1, kind="transcript", language="en",
        revision=1, text=text, status="final", start_ms=0, end_ms=100,
    )
    assert c.text == text
    assert CaptionData.model_validate_json(c.model_dump_json()).text == text


@pytest.mark.parametrize("text", ["a" * 8193, "á" * 4097, "🙂" * 2049])
def test_caption_rejects_text_over_utf8_byte_limit(text):
    with pytest.raises(ValidationError):
        CaptionData(
            segment_id="seg-1", segment_seq=1, kind="transcript", language="en",
            revision=1, text=text, status="final", start_ms=0, end_ms=100,
        )


@pytest.mark.parametrize("start,end", [(None, 100), (100, None), (200, 100)])
def test_gap_rejects_incomplete_or_reversed_interval(start, end):
    with pytest.raises(ValidationError):
        GapData(gap_id="gap-1", start_ms=start, end_ms=end, reason="overload")


@pytest.mark.parametrize("start,end", [(None, None), (0, 0), (0, 100)])
def test_gap_accepts_unknown_or_ordered_interval(start, end):
    gap = GapData(gap_id="gap-1", start_ms=start, end_ms=end, reason="overload")
    assert GapData.model_validate_json(gap.model_dump_json()) == gap


@pytest.mark.parametrize("field", ["segment_seq", "revision", "source_revision", "start_ms", "end_ms"])
@pytest.mark.parametrize("invalid", [True, "1", 1.0, -1, 2**53])
def test_caption_rejects_non_integer_or_unsafe_numbers(field, invalid):
    data = dict(
        segment_id="seg-1", segment_seq=1, kind="translation", language="es",
        revision=1, source_revision=1, text="hola", status="final", start_ms=0, end_ms=100,
    )
    data[field] = invalid
    with pytest.raises(ValidationError):
        CaptionData.model_validate_json(json.dumps(data))


@pytest.mark.parametrize("invalid", [True, "1", 1.0, -1, 2**53, 2**53 + 1])
def test_envelope_rejects_non_integer_or_unsafe_sequence(invalid):
    data = json.loads((Path(__file__).parents[1] / "fixtures/snapshot_empty.json").read_text())
    data["seq"] = invalid
    with pytest.raises(ValidationError):
        SessionSnapshotEvent.model_validate_json(json.dumps(data))


@pytest.mark.parametrize("seq", [0, 2**53 - 1])
def test_envelope_accepts_safe_sequence_boundaries(seq):
    data = json.loads((Path(__file__).parents[1] / "fixtures/snapshot_empty.json").read_text())
    data["seq"] = seq
    event = SessionSnapshotEvent.model_validate_json(json.dumps(data))
    assert event.seq == seq


@pytest.mark.parametrize("field", ["start_ms", "end_ms"])
@pytest.mark.parametrize("invalid", [True, "1", 1.0, -1, 2**53])
def test_gap_rejects_non_integer_or_unsafe_time(field, invalid):
    data = dict(gap_id="gap-1", start_ms=0, end_ms=100, reason="overload")
    data[field] = invalid
    with pytest.raises(ValidationError):
        GapData.model_validate(data)


def test_session_rejects_duplicate_translation_languages():
    with pytest.raises(ValidationError, match="repetidos"):
        Session(id="s1", title="Charla", source_language="en", translation_languages=["es", "es"], status="live")


def test_all_shared_fixtures_still_validate():
    adapter = TypeAdapter(Event)
    for path in (Path(__file__).parents[1] / "fixtures").glob("*.json"):
        data = json.loads(path.read_text())
        if path.name == "catalog.json":
            SessionCatalog.model_validate(data)
        elif path.name == "session_detail.json":
            Session.model_validate(data)
        elif isinstance(data, list):
            for event in data:
                adapter.validate_python(event)
        else:
            adapter.validate_python(data)
