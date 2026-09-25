import base64

import httpx
import pytest

from decilo import gemini, providers, stt, translate


@pytest.fixture(autouse=True)
def clean_config(monkeypatch):
    for name in ('DECILO_AI_PROVIDER', 'DECILO_STT_PROVIDER',
                 'DECILO_TRANSLATION_PROVIDER', 'DECILO_GEMINI_MODEL'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('GEMINI_API_KEY', 'test-secret')


def test_selection(monkeypatch):
    assert providers.provider('stt') == 'local'
    monkeypatch.setenv('DECILO_AI_PROVIDER', 'gemini')
    monkeypatch.setenv('DECILO_STT_PROVIDER', 'local')
    assert providers.provider('stt') == 'local'
    assert providers.provider('translation') == 'gemini'
    monkeypatch.setenv('DECILO_STT_PROVIDER', 'typo')
    with pytest.raises(ValueError):
        providers.provider('stt')


def test_missing_key(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY')
    with pytest.raises(ValueError, match='GEMINI_API_KEY'):
        gemini.request([], '')


def response(text='Hola'):
    return httpx.Response(200, json={'candidates': [{'finishReason': 'STOP',
        'content': {'parts': [{'text': 'private reasoning', 'thought': True}, {'text': text}]}}]})


@pytest.mark.parametrize('resp', [httpx.Response(401, text='test-secret'),
    httpx.Response(429), httpx.Response(200, json={}),
    httpx.Response(200, json={'candidates': [{'finishReason': 'MAX_TOKENS'}]}),
    response('')])
def test_errors_are_sanitized(resp):
    with pytest.raises(RuntimeError) as exc:
        gemini.result(resp)
    assert 'test-secret' not in str(exc.value)


def test_audio_dispatch_and_payload(monkeypatch, tmp_path):
    monkeypatch.setenv('DECILO_STT_PROVIDER', 'gemini')
    path = tmp_path / 'audio.wav'
    path.write_bytes(b'RIFF-test')
    def post(self, url, *, headers, json):
        assert 'test-secret' not in url
        assert url.endswith('/gemini-3.1-flash-lite:generateContent')
        assert headers['x-goog-api-key'] == 'test-secret'
        audio = json['contents'][0]['parts'][0]['inlineData']
        assert base64.b64decode(audio['data']) == path.read_bytes()
        assert audio['mimeType'] == 'audio/wav'
        return response('Hello')
    monkeypatch.setattr(httpx.Client, 'post', post)
    monkeypatch.setattr(stt, '_get_model', lambda *_: pytest.fail('Local model loaded'))
    assert stt.transcribe(path, 'en') == 'Hello'


@pytest.mark.asyncio
async def test_translation_dispatch(monkeypatch):
    monkeypatch.setenv('DECILO_TRANSLATION_PROVIDER', 'gemini')
    async def post(self, url, *, headers, json):
        assert json['contents'][0]['parts'] == [{'text': 'Hello'}]
        return response()
    monkeypatch.setattr(httpx.AsyncClient, 'post', post)
    assert await translate.translate('Hello') == 'Hola'


def test_dotenv_does_not_override_environment(monkeypatch, tmp_path):
    path = tmp_path / '.env'
    path.write_text('DECILO_AI_PROVIDER=gemini\nGEMINI_API_KEY=file-key\n')
    monkeypatch.setenv('DECILO_AI_PROVIDER', 'local')
    original = providers.load_dotenv
    monkeypatch.setattr(providers, 'load_dotenv', lambda _, **kw: original(path, **kw))
    providers.load_config()
    assert providers.provider('stt') == 'local'
    assert gemini.request([], '')[1]['x-goog-api-key'] == 'test-secret'
