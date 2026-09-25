"""Genera fixtures/*.json a partir de los modelos Pydantic del contrato.

Garantiza que las fixtures siempre validen contra src/decilo/models.py.
Uso: uv run scripts/gen_fixtures.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from decilo.models import (
    CaptionData,
    CaptionUpsertEvent,
    DiscardedCaption,
    GapData,
    Session,
    SessionCatalog,
    SessionErrorData,
    SessionErrorEvent,
    SessionGapEvent,
    SessionStatusData,
    SessionStatusEvent,
    SnapshotData,
    SessionSnapshotEvent,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"
T0 = datetime(2026, 9, 25, 1, 0, 0, tzinfo=timezone.utc)


def write(name: str, model) -> None:
    (FIXTURES / name).write_text(model.model_dump_json(indent=2) + "\n")
    print(f"fixtures/{name}")


def main() -> None:
    FIXTURES.mkdir(exist_ok=True)

    session_en = Session(
        id="konex-sala-1-charla-1",
        title="Building reliable systems",
        source_language="en",
        translation_languages=["es"],
        target_locale="es-AR",
        status="live",
    )
    session_es = Session(
        id="konex-sala-2-charla-1",
        title="Arquitectura de microservicios",
        source_language="es",
        translation_languages=[],
        target_locale=None,
        status="live",
    )

    write("catalog.json", SessionCatalog(sessions=[session_en, session_es]))
    write("session_detail.json", session_en)

    write(
        "snapshot_empty.json",
        SessionSnapshotEvent(
            session_id=session_en.id,
            stream_id="run-1",
            seq=0,
            emitted_at=T0,
            data=SnapshotData(session=session_en, captions=[], gaps=[], history_truncated=False),
        ),
    )

    transcript_provisional = CaptionUpsertEvent(
        session_id=session_en.id,
        stream_id="run-1",
        seq=1,
        emitted_at=T0,
        data=CaptionData(
            segment_id="seg-1",
            segment_seq=1,
            kind="transcript",
            language="en",
            revision=1,
            source_revision=None,
            text="We need",
            status="provisional",
            start_ms=0,
            end_ms=400,
            speaker_id=None,
            boundary_reason=None,
        ),
    )
    write("caption_transcript_provisional.json", transcript_provisional)

    transcript_final = CaptionUpsertEvent(
        session_id=session_en.id,
        stream_id="run-1",
        seq=2,
        emitted_at=T0,
        data=CaptionData(
            segment_id="seg-1",
            segment_seq=1,
            kind="transcript",
            language="en",
            revision=2,
            source_revision=None,
            text="We need another code review.",
            status="final",
            start_ms=0,
            end_ms=950,
            speaker_id=None,
            boundary_reason="pause",
        ),
    )
    write("caption_transcript_final.json", transcript_final)

    translation_final = CaptionUpsertEvent(
        session_id=session_en.id,
        stream_id="run-1",
        seq=3,
        emitted_at=T0,
        data=CaptionData(
            segment_id="seg-1",
            segment_seq=1,
            kind="translation",
            language="es",
            revision=1,
            source_revision=2,
            text="Necesitamos otra revision de codigo.",
            status="final",
            start_ms=0,
            end_ms=950,
            speaker_id=None,
            boundary_reason="pause",
        ),
    )
    write("caption_translation_final.json", translation_final)

    write(
        "session_status_degraded.json",
        SessionStatusEvent(
            session_id=session_en.id,
            stream_id="run-1",
            seq=4,
            emitted_at=T0,
            data=SessionStatusData(session=session_en.model_copy(update={"status": "degraded"})),
        ),
    )

    write(
        "session_error.json",
        SessionErrorEvent(
            session_id=session_en.id,
            stream_id="run-1",
            seq=5,
            emitted_at=T0,
            data=SessionErrorData(
                code="inference_unavailable",
                message="El motor de traduccion no responde",
                retryable=True,
            ),
        ),
    )

    write(
        "session_gap.json",
        SessionGapEvent(
            session_id=session_en.id,
            stream_id="run-1",
            seq=6,
            emitted_at=T0,
            data=GapData(
                gap_id="gap-1",
                start_ms=950,
                end_ms=1800,
                reason="overload",
                discard_captions=[
                    DiscardedCaption(segment_id="seg-2", kind="transcript", language="en"),
                ],
            ),
        ),
    )

    # Secuencia completa para probar un reductor de eventos de punta a punta.
    sequence = [
        json.loads(SessionSnapshotEvent(
            session_id=session_en.id, stream_id="run-1", seq=0, emitted_at=T0,
            data=SnapshotData(session=session_en, captions=[], gaps=[], history_truncated=False),
        ).model_dump_json()),
        json.loads(transcript_provisional.model_dump_json()),
        json.loads(transcript_final.model_dump_json()),
        json.loads(translation_final.model_dump_json()),
    ]
    (FIXTURES / "event_sequence.json").write_text(json.dumps(sequence, indent=2) + "\n")
    print("fixtures/event_sequence.json")


if __name__ == "__main__":
    main()
