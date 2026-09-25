"""Tests del estado retenido del servidor (sin modelos de IA)."""

import pytest

from decilo.models import CaptionData, GapData, Session
from decilo.stream import MAX_GAPS, MAX_SEGMENTS, SessionStream


def make_session(**overrides) -> Session:
    defaults = dict(id="s1", title="Charla", source_language="en", translation_languages=["es"], status="live")
    defaults.update(overrides)
    return Session(**defaults)


def make_caption(**overrides) -> CaptionData:
    defaults = dict(
        segment_id="seg-1", segment_seq=1, kind="transcript", language="en",
        revision=1, source_revision=None, text="hola", status="final",
        start_ms=0, end_ms=100,
    )
    defaults.update(overrides)
    return CaptionData(**defaults)


def test_snapshot_seq_zero_and_not_consumed():
    stream = SessionStream(make_session())
    snap = stream.snapshot()
    assert snap.seq == 0
    assert snap.type == "session.snapshot"
    # snapshot no incrementa el contador de seq
    assert stream.seq == 0


def test_upsert_increments_seq_starting_after_snapshot():
    stream = SessionStream(make_session())
    event = stream.upsert_caption(make_caption(status="provisional"))
    assert event.seq == 1
    event2 = stream.upsert_caption(make_caption(revision=2, text="hola de nuevo", status="provisional"))
    assert event2.seq == 2


def test_final_is_immutable():
    stream = SessionStream(make_session())
    stream.upsert_caption(make_caption(status="final"))
    with pytest.raises(ValueError):
        stream.upsert_caption(make_caption(revision=2, text="cambio", status="final"))


def test_translation_invalidated_when_original_advances():
    stream = SessionStream(make_session())
    stream.upsert_caption(make_caption(revision=1, status="provisional", text="We need"))
    stream.upsert_caption(
        make_caption(kind="translation", language="es", revision=1, source_revision=1,
                     status="provisional", text="Necesitamos")
    )
    snap = stream.snapshot()
    keys = {(c.kind, c.language, c.revision) for c in snap.data.captions}
    assert ("translation", "es", 1) in keys

    # El original avanza de revision; la traduccion vieja debe desaparecer.
    stream.upsert_caption(make_caption(revision=2, status="final", text="We need review"))
    snap = stream.snapshot()
    kinds = [c.kind for c in snap.data.captions]
    assert kinds.count("translation") == 0


def test_final_translation_survives_original_advancing():
    stream = SessionStream(make_session())
    stream.upsert_caption(make_caption(revision=1, status="final", text="We need review"))
    stream.upsert_caption(
        make_caption(kind="translation", language="es", revision=1, source_revision=1,
                     status="final", text="Necesitamos revision")
    )
    # Un original ya final no debería volver a cambiar, pero si algo más
    # (defensivo) lo intentara, la traduccion final no se borra.
    with pytest.raises(ValueError):
        stream.upsert_caption(make_caption(revision=2, status="final", text="otro"))
    snap = stream.snapshot()
    assert any(c.kind == "translation" and c.status == "final" for c in snap.data.captions)


def test_retention_evicts_oldest_segments():
    stream = SessionStream(make_session())
    for i in range(1, MAX_SEGMENTS + 5):
        stream.upsert_caption(make_caption(segment_id=f"seg-{i}", segment_seq=i, text=f"texto {i}"))
    snap = stream.snapshot()
    assert len(snap.data.captions) == MAX_SEGMENTS
    assert snap.data.history_truncated is True
    remaining_ids = {c.segment_id for c in snap.data.captions}
    assert "seg-1" not in remaining_ids
    assert f"seg-{MAX_SEGMENTS + 4}" in remaining_ids


def test_gap_discards_provisional_but_not_final():
    stream = SessionStream(make_session())
    stream.upsert_caption(make_caption(status="provisional", text="parcial"))
    stream.record_gap(
        GapData(gap_id="g1", start_ms=0, end_ms=100, reason="overload",
                discard_captions=[{"segment_id": "seg-1", "kind": "transcript", "language": "en"}])
    )
    snap = stream.snapshot()
    assert len(snap.data.captions) == 0

    stream2 = SessionStream(make_session())
    stream2.upsert_caption(make_caption(status="final", text="definitivo"))
    stream2.record_gap(
        GapData(gap_id="g1", start_ms=0, end_ms=100, reason="overload",
                discard_captions=[{"segment_id": "seg-1", "kind": "transcript", "language": "en"}])
    )
    snap2 = stream2.snapshot()
    assert len(snap2.data.captions) == 1


def test_gaps_capped_at_max():
    stream = SessionStream(make_session())
    for i in range(MAX_GAPS + 3):
        stream.record_gap(GapData(gap_id=f"g{i}", start_ms=None, end_ms=None, reason="overload"))
    assert len(stream.gaps) == MAX_GAPS
    assert stream.history_truncated is True


def test_duplicates_and_old_revisions_do_not_advance_sequence():
    stream = SessionStream(make_session())
    original = make_caption(revision=2, status="provisional")
    stream.upsert_caption(original)
    assert stream.upsert_caption(original) is None
    assert stream.upsert_caption(make_caption(revision=1, status="provisional")) is None
    assert stream.seq == 1
    final = make_caption(revision=3, status="final")
    stream.upsert_caption(final)
    assert stream.upsert_caption(final) is None
    assert stream.seq == 2
    with pytest.raises(ValueError):
        stream.upsert_caption(final.model_copy(update={"text": "mutado"}))
    assert stream.snapshot().data.captions == [final]


@pytest.mark.parametrize("bad", [
    dict(kind="translation", language="es", source_revision=1),
    dict(kind="transcript", language="es"),
])
def test_invalid_first_caption_does_not_mutate_stream(bad):
    stream = SessionStream(make_session())
    before = stream.snapshot().data
    with pytest.raises(ValueError):
        stream.upsert_caption(make_caption(**bad))
    assert stream.seq == 0
    assert stream.snapshot().data == before


def test_translation_must_match_current_final_original_and_timestamps():
    stream = SessionStream(make_session())
    stream.upsert_caption(make_caption(status="provisional", revision=2))
    with pytest.raises(ValueError):
        stream.upsert_caption(make_caption(kind="translation", language="es", source_revision=2))
    stream.upsert_caption(make_caption(status="final", revision=3))
    old = make_caption(kind="translation", language="es", source_revision=2)
    assert stream.upsert_caption(old) is None
    assert stream.seq == 2
    for changes in (dict(source_revision=4), dict(source_revision=3, end_ms=200)):
        with pytest.raises(ValueError):
            stream.upsert_caption(old.model_copy(update=changes))
    assert stream.seq == 2
    assert len(stream.snapshot().data.captions) == 1


def test_invalidated_translation_keeps_its_revision_counter():
    stream = SessionStream(make_session())
    stream.upsert_caption(make_caption(status="provisional"))
    stream.upsert_caption(make_caption(kind="translation", language="es", source_revision=1, revision=3, status="provisional"))
    stream.upsert_caption(make_caption(revision=2))
    assert stream.upsert_caption(make_caption(kind="translation", language="es", source_revision=2, revision=2)) is None
    assert len(stream.snapshot().data.captions) == 1
    assert stream.upsert_caption(make_caption(kind="translation", language="es", source_revision=2, revision=4)) is not None


def test_snapshot_evicts_complete_segments_to_fit_utf8_budget():
    from decilo.stream import MAX_MESSAGE_BYTES
    stream = SessionStream(make_session())
    for i in range(1, 101):
        stream.upsert_caption(make_caption(segment_id=str(i), segment_seq=i, text="á" * 4096))
        stream.upsert_caption(make_caption(segment_id=str(i), segment_seq=i, text="🙂" * 2048,
                                          kind="translation", language="es", source_revision=1))
    snapshot = stream.snapshot()
    assert len(snapshot.model_dump_json().encode("utf-8")) <= MAX_MESSAGE_BYTES
    assert snapshot.data.history_truncated
    assert len(snapshot.data.captions) < 200
    ids = {c.segment_id for c in snapshot.data.captions}
    assert all(sum(c.segment_id == sid for c in snapshot.data.captions) == 2 for sid in ids)
    assert "100" in ids
    before = stream.seq
    assert stream.upsert_caption(make_caption(segment_id="1", segment_seq=1, revision=2)) is None
    assert stream.seq == before
    assert len(stream._segments) == len(ids)
    assert len(stream._revisions) == len(snapshot.data.captions)


def test_gap_removes_dependent_translations_and_cannot_resurrect_original():
    stream = SessionStream(make_session())
    stream.upsert_caption(make_caption(status="provisional"))
    stream.upsert_caption(make_caption(kind="translation", language="es", source_revision=1, status="provisional"))
    stream.record_gap(GapData(gap_id="g", reason="overload", discard_captions=[
        dict(segment_id="seg-1", kind="transcript", language="en"),
    ]))
    assert stream.snapshot().data.captions == []
    assert stream.upsert_caption(make_caption(revision=2)) is None


def test_segment_identity_and_start_are_immutable():
    stream = SessionStream(make_session())
    stream.upsert_caption(make_caption(status="provisional"))
    for changes in (dict(segment_seq=2), dict(start_ms=1), dict(end_ms=50)):
        with pytest.raises(ValueError):
            stream.upsert_caption(make_caption(revision=2, **changes))
    assert stream.seq == 1


def test_snapshot_drops_old_gaps_if_their_serialized_size_exceeds_budget(monkeypatch):
    import decilo.stream as module
    stream = SessionStream(make_session())
    monkeypatch.setattr(module, "MAX_MESSAGE_BYTES", 1500)
    for i in range(10):
        stream.record_gap(GapData(gap_id=f"gap-{i}" + "x" * 250, reason="overload"))
    snap = stream.snapshot()
    assert len(snap.model_dump_json().encode()) <= 1500
    assert snap.data.history_truncated
    assert 0 < len(snap.data.gaps) < 10
    assert snap.data.gaps[-1].gap_id.startswith("gap-9")
