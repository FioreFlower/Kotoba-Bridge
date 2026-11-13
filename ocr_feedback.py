"""Lossless OCR preview plus explicitly untrusted spacing suggestions, never transport."""
import re

# A single ASCII space between Japanese letters only. Punctuation, line boundaries,
# multiple spaces, ideographic spaces and Latin/number boundaries are preserved.
_JAPANESE = r'\u3041-\u3096\u30A1-\u30FA\u30FC\u3400-\u4DBF\u4E00-\u9FFF'
_GAP = re.compile(r'(?<=[' + _JAPANESE + r']) (?=[' + _JAPANESE + r'])')

def spacing_candidate(raw):
    return _GAP.subn('', raw)

def preview_text(raw):
    candidate, count = spacing_candidate(raw)
    result = '[OCR 원본 · 공백 보존]\n' + (raw if raw else '[인식된 글자 없음]')
    if count:
        result += ('\n\n[공백 정리 후보 · 의미 검증 안 됨 · 자동 적용 안 함]\n' + candidate
                   + f'\n\n일본어 문자 사이 단일 반각 공백 {count}개를 제안상 제거했습니다. '
                     '띄어쓰기 의도는 판단할 수 없습니다. 원본을 확인하세요.')
    result += '\n\n[로컬 OCR 미리보기 · 번역 API 전송 없음]'
    return result

def region_hint(region, monitor):
    large = (region.height > monitor['height'] * .35 or
             region.width * region.height > monitor['width'] * monitor['height'] * .3)
    advice = ('넓은 영역입니다. 배경·메뉴 문자가 섞이지 않았는지 확인하세요.' if large else
              '글자가 잘리지 않도록 작은 여백을 두고 모든 대사 줄을 포함하세요.')
    return f'선택: {region.left}, {region.top} · {region.width}×{region.height} 물리 픽셀\n{advice}'

def usage_label(calls, chars, *, demo, local=False):
    if demo:
        return f'오프라인 데모 · 모의 사용량 {calls}/100회 · {chars}/10,000자 · 외부 전송 없음 · API 과금 없음'
    prefix = '로컬 번역 · 세션 처리 한도' if local else '외부 API · 세션 예약 사용량 (실제 청구액 아님)'
    return f'{prefix} {calls}/100회 · {chars}/10,000자'
