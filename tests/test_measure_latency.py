from scripts.measure_latency import word_error_rate


def test_wer_ignores_case_punctuation_and_counts_word_edits():
    assert word_error_rate('Hola, MUNDO!', 'hola mundo')['wer'] == 0
    assert word_error_rate('one two three', 'one four')['errors'] == 2
    assert word_error_rate('one', 'one extra')['wer'] == 1
    assert word_error_rate('', '')['wer'] is None


def test_metrics_count_each_caption_once_for_first_and_final():
    from scripts.measure_latency import caption_summaries
    def event(revision, elapsed, status, kind='translation', segment='seg-1'):
        return {'elapsed_seconds': elapsed, 'event': {'type': 'caption.upsert', 'data': {
            'segment_id': segment, 'kind': kind, 'language': 'es', 'revision': revision,
            'status': status, 'start_ms': 1000, 'end_ms': 2000}}}
    result = caption_summaries([
        event(1, 3, 'provisional'), event(2, 3.1, 'provisional'), event(3, 4, 'final'),
        event(1, 5, 'provisional', segment='seg-2'),
    ])
    assert result['first_summary']['translation/es']['n'] == 2
    assert result['summary']['translation/es'] == {'n': 1, 'p50': 2, 'p95': 2, 'max': 2}
    assert result['final_from_start']['translation/es']['p50'] == 3
    assert result['unfinished_captions'] == 1
