"""User-controlled local study data. Never calls translation services."""
import json
from pathlib import Path
from urllib.parse import quote

MAX_ITEMS = 500

def dictionary_url(term):
    term = term.strip()
    if not term or len(term) > 100:
        raise ValueError('사전 검색어는 1~100자로 선택하세요.')
    return 'https://ja.wiktionary.org/wiki/' + quote(term, safe='')

class StudyStore:
    def __init__(self):
        self.history = []
        self.cards = []

    def record(self, source, translation):
        self.history.append({'source':source, 'translation':translation})
        self.history = self.history[-MAX_ITEMS:]

    def save(self, term, source, translation):
        if not term.strip() or len(term) > 2000:
            raise ValueError('저장할 단어나 문장을 선택하세요 (최대 2,000자).')
        card = {'term':term.strip(), 'source':source, 'translation':translation}
        if card not in self.cards:
            if len(self.cards) >= MAX_ITEMS: raise ValueError('복습 저장 한도는 500개입니다.')
            self.cards.append(card)

    def export(self, path):
        # Explicit user-selected file, no API keys or automatic dialogue history.
        Path(path).write_text(json.dumps({'version':1,'cards':self.cards}, ensure_ascii=False, indent=2),encoding='utf-8')

    def load(self, path):
        with Path(path).open('rb') as file:
            raw = file.read(2_000_001)
        if len(raw)>2_000_000: raise ValueError('복습 파일은 2MB 이하여야 합니다.')
        data=json.loads(raw)
        if data.get('version') != 1 or not isinstance(data.get('cards'),list) or len(data['cards']) > MAX_ITEMS:
            raise ValueError('지원하지 않는 복습 파일입니다.')
        valid=[]
        for card in data['cards']:
            if not isinstance(card,dict) or set(card)!={'term','source','translation'}:
                raise ValueError('잘못된 복습 항목입니다.')
            if not all(isinstance(v,str) and len(v)<=20000 for v in card.values()):
                raise ValueError('잘못된 복습 텍스트입니다.')
            valid.append(card)
        self.cards=valid
