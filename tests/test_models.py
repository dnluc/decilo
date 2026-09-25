"""Tests de los modelos del contrato (sin modelos de IA, corren en CI)."""

import pytest
from pydantic import ValidationError

from decilo.models import CaptionData, Session


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
