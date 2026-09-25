from scripts.measure_latency import word_error_rate


def test_wer_ignores_case_punctuation_and_counts_word_edits():
    assert word_error_rate('Hola, MUNDO!', 'hola mundo')['wer'] == 0
    assert word_error_rate('one two three', 'one four')['errors'] == 2
    assert word_error_rate('one', 'one extra')['wer'] == 1
    assert word_error_rate('', '')['wer'] is None
