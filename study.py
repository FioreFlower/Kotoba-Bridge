"""User-controlled local study data. Never calls translation services."""
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import quote

MAX_ITEMS = 500
MAX_FILE_BYTES = 2_000_000
FIELD_LIMITS = {'term': 2000, 'source': 2000, 'translation': 20000}


def dictionary_url(term):
    if not isinstance(term, str):
        raise ValueError('사전 검색어는 텍스트여야 합니다.')
    term = term.strip()
    if not term or len(term) > 100:
        raise ValueError('사전 검색어는 1~100자로 선택하세요.')
    return 'https://ja.dict.naver.com/#/search?query=' + quote(term, safe='')


def validate_text(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > FIELD_LIMITS[field]:
        raise ValueError('비어 있거나 길이 제한을 넘은 복습 텍스트입니다.')
    return value


def validate_card(card):
    if not isinstance(card, dict) or set(card) != set(FIELD_LIMITS):
        raise ValueError('잘못된 복습 항목입니다.')
    return {field: validate_text(card[field], field) for field in FIELD_LIMITS}


class StudyStore:
    def __init__(self):
        self.history = []
        self.cards = []

    def record(self, source, translation):
        validate_text(source, 'source')
        validate_text(translation, 'translation')
        self.history.append({'source': source, 'translation': translation})
        self.history = self.history[-MAX_ITEMS:]

    def save(self, term, source, translation):
        validate_text(term, 'term')
        card = validate_card({'term': term.strip(), 'source': source, 'translation': translation})
        if card not in self.cards:
            if len(self.cards) >= MAX_ITEMS:
                raise ValueError('복습 저장 한도는 500개입니다.')
            self.cards.append(card)

    def export(self, path):
        # Validate before touching the selected destination. No keys or history export.
        if len(self.cards) > MAX_ITEMS:
            raise ValueError('복습 저장 한도는 500개입니다.')
        cards = [validate_card(card) for card in self.cards]
        data = json.dumps({'version': 1, 'cards': cards}, ensure_ascii=False, indent=2).encode('utf-8')
        if len(data) > MAX_FILE_BYTES:
            raise ValueError('복습 파일이 2MB를 초과합니다. 일부 카드를 삭제한 뒤 내보내세요.')
        target = Path(path)
        temporary = None
        try:
            # Same directory guarantees an atomic replace on the same filesystem.
            with tempfile.NamedTemporaryFile(mode='wb', dir=target.parent, prefix='.' + target.name + '.', suffix='.tmp', delete=False) as output:
                temporary = Path(output.name)
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, target)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def load(self, path):
        with Path(path).open('rb') as file:
            raw = file.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError('복습 파일은 2MB 이하여야 합니다.')
        try:
            data = json.loads(raw.decode('utf-8-sig'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError('UTF-8 복습 JSON 파일이 아닙니다.') from exc
        if (not isinstance(data, dict) or set(data) != {'version', 'cards'}
                or type(data['version']) is not int or data['version'] != 1
                or not isinstance(data['cards'], list) or len(data['cards']) > MAX_ITEMS):
            raise ValueError('지원하지 않는 복습 파일입니다.')
        valid = [validate_card(card) for card in data['cards']]
        self.cards = valid  # Commit only after the entire document validates.
