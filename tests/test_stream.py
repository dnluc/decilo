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
