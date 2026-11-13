"""Network-independent state and explicitly enabled DeepL transport."""
import json
import re
import time
import ssl
import urllib.request
import urllib.error
from collections import OrderedDict
from dataclasses import dataclass

class ReaderError(Exception):
    pass

@dataclass(frozen=True)
class Region:
    left: int
    top: int
    width: int
    height: int

    def __post_init__(self):
        if not (20 <= self.width <= 3840 and 20 <= self.height <= 2160):
            raise ReaderError('영역 크기는 20×20 이상, 3840×2160 이하여야 합니다.')

    def overlaps(self, other):
        return (self.left < other.left + other.width and other.left < self.left + self.width
                and self.top < other.top + other.height and other.top < self.top + self.height)


def normalize(text):
    return re.sub(r'\s+', ' ', text).strip()

class StableText:
    """Require unchanged OCR for >=0.9 seconds; blanks break stability."""
    def __init__(self, delay=0.9):
        self.delay, self.value, self.since, self.emitted = delay, '', 0, ''

    def feed(self, value, now):
        value = normalize(value)
        if value != self.value:
            self.value, self.since = value, now
        if not value:
            self.emitted = ''
            return None
        if value != self.emitted and now - self.since >= self.delay:
            self.emitted = value
            return value
        return None

class Budget:
    """Conservative session reservations include requests with uncertain outcomes."""
    def __init__(self, chars=10000, calls=100, interval=3.0):
        self.limit_chars, self.limit_calls, self.interval = chars, calls, interval
        self.chars = self.calls = 0
        self.last = float('-inf')

    def reserve(self, text, now):
        if now - self.last < self.interval:
            raise ReaderError('호출 간격 제한: 잠시 후 다시 시작하세요.')
        if self.calls + 1 > self.limit_calls or self.chars + len(text) > self.limit_chars:
            raise ReaderError('세션 한도 도달: 번역을 중지했습니다.')
        self.calls += 1
        self.chars += len(text)
        self.last = now

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

class DeepL:
    def __init__(self, key, pro=False, opener=None):
        if not key.strip():
            raise ReaderError('API 키를 입력하세요.')
        self._key = key.strip()
        self.url = 'https://api.deepl.com/v2/translate' if pro else 'https://api-free.deepl.com/v2/translate'
        # Fixed HTTPS endpoint, no redirects or environment proxy credential forwarding.
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.keylog_filename = None
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), urllib.request.HTTPSHandler(context=context))

    def translate(self, text, context):
        data = json.dumps({'text': [text], 'source_lang': 'JA', 'target_lang': 'KO',
                           'context': context, 'split_sentences': 'nonewlines'}, ensure_ascii=False).encode('utf-8')
        request = urllib.request.Request(self.url, data=data, headers={
            'Authorization': 'DeepL-Auth-Key ' + self._key, 'Content-Type': 'application/json'})
        try:
            with self.opener.open(request, timeout=15) as response:
                payload = json.loads(response.read(65537))
            result = payload['translations'][0]['text']
            if not isinstance(result, str) or not result.strip() or len(result) > 20000:
                raise ValueError()
            return result
        except urllib.error.HTTPError as exc:
            messages = {403: '키 또는 계정 인증 실패', 429: '서버 호출 제한', 456: 'DeepL 사용량 한도 초과'}
            raise ReaderError(messages.get(exc.code, '번역 서버 HTTP 오류') + ': 자동 재시도하지 않습니다.') from None
        except Exception:
            raise ReaderError('네트워크 시간 초과 또는 응답 오류: 과금 여부가 불확실하여 자동 재시도하지 않습니다.') from None

class Demo:
    def translate(self, text, context):
        return {'こんにちは。': '안녕하세요.', '一緒に帰りましょう。': '같이 돌아가요.',
                '明日、またここで会おう。': '내일 여기서 다시 만나자.'}.get(text, '[데모: 실제 번역 아님] ' + text)

class Translator:
    def __init__(self, provider, budget=None):
        self.provider, self.budget = provider, budget or Budget()
        self.history, self.cache = [], OrderedDict()

    def translate(self, text, now=None):
        text = normalize(text)
        if not text or len(text) > 2000:
            raise ReaderError('인식 텍스트가 비어 있거나 2,000자를 초과합니다.')
        context = '\n'.join(self.history)[-1500:]
        key = (text, context)
        if key in self.cache:
            return self.cache[key]
        self.budget.reserve(text, time.monotonic() if now is None else now)
        result = self.provider.translate(text, context)
        self.cache[key] = result
        if len(self.cache) > 128:
            self.cache.popitem(last=False)
        self.history = (self.history + [text])[-3:]
        return result
