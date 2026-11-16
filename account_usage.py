"""Format DeepL-returned account data only. No local billing estimates."""
from datetime import datetime

def format_usage(data):
    def number(v):
        if type(v) is not int or v<0:raise ValueError('잘못된 사용량')
        return f'{v:,}'
    def limit(v):
        if v is None:return 'API 미제공'
        return '설정 안 됨' if v==1_000_000_000_000 else number(v)+'자'
    stamp=datetime.fromisoformat(data['checked_at'].replace('Z','+00:00')).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
    out=f"DeepL 계정 · 이번 청구 기간 {number(data['character_count'])}자 · 한도 {limit(data.get('character_limit'))}"
    if 'api_key_character_count' in data:
        out+=f"\n현재 키 {number(data['api_key_character_count'])}자 · 키 한도 {limit(data.get('api_key_character_limit'))}"
    return out+f'\n조회 {stamp} · API 반영에 몇 분 걸릴 수 있음 · 청구 금액 아님'
