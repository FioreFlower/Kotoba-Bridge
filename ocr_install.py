"""Offline OCR setup guidance; never download, open URLs, or execute installers.

UI callers may display these strings and offer links on an explicit user click.
This module does not attest to the safety of a user-selected executable.
"""

REVIEWED_ON = '2026-11-13'
PACKAGE_ID = 'UB-Mannheim.TesseractOCR'
DOCUMENTATION_URL = 'https://tesseract-ocr.github.io/tessdoc/Installation.html'
PROVIDER_URL = 'https://github.com/UB-Mannheim/tesseract/wiki'
MODEL_URL = 'https://github.com/tesseract-ocr/tessdata_fast'
WINGET_MANIFEST_URL = ('https://github.com/microsoft/winget-pkgs/blob/master/'
    'manifests/u/UB-Mannheim/TesseractOCR/5.4.0.20240606/'
    'UB-Mannheim.TesseractOCR.installer.yaml')


def get_install_guide():
    """Return independent display data; no machine state or network is accessed."""
    return {
        'reviewed_on': REVIEWED_ON,
        'steps': [
            '1. OCR 없이도 데모를 사용할 수 있습니다. 게임 인식이 필요할 때 아래 공식 Tesseract 설치 문서를 여세요.',
            '2. 공식 문서가 연결하는 UB Mannheim 안내에서 Windows 64비트 설치 파일의 출처·버전·보안 표시를 확인하세요. 이것은 제3자 배포본입니다.',
            '3. 직접 설치할 때 기본 설치 폴더 또는 새 전용 폴더를 사용하세요. 게임·문서·앱이 있는 기존 폴더를 선택하지 마세요. 공급자는 제거 시 설치 폴더 전체 삭제를 경고합니다.',
            '4. 설치 구성에서 일본어 Japanese / jpn 언어 데이터를 선택하세요. 구성 이름은 버전에 따라 다를 수 있습니다. 언어팩 다운로드에는 인터넷이 필요할 수 있습니다.',
            '5. 앱으로 돌아와 OCR 다시 확인을 누르세요. 발견되지 않으면 설치한 tesseract.exe를 직접 선택하세요. 직접 선택한 실행파일은 검사 시 실행되므로 출처를 확인하세요.',
            '6. jpn이 없으면 설치 프로그램의 언어 구성 또는 공식 모델 저장소 안내를 확인하세요. 정상 확인 후 로컬 OCR 미리보기로 인식 결과를 점검하세요. 언어 목록 통과는 인식 품질 보증이 아닙니다.',
        ],
        'links': [
            ('Tesseract 공식 설치 문서', DOCUMENTATION_URL),
            ('UB Mannheim Windows 배포 안내 (제3자)', PROVIDER_URL),
            ('공식 언어 모델과 라이선스', MODEL_URL),
            ('Microsoft WinGet manifest 검토 자료', WINGET_MANIFEST_URL),
        ],
        'privacy': '안내 표시는 오프라인입니다. 링크를 직접 열면 해당 사이트에 접속 정보가 전달됩니다. OCR 설치·언어팩 다운로드는 번역 API와 별개이며 게임 이미지·대사·API 키를 보내지 않습니다. 설치 후 OCR 검사는 로컬 실행입니다.',
        'winget_note': 'WinGet 자동 설치는 제공하지 않습니다. 확인한 UB-Mannheim.TesseractOCR 5.4.0.20240606 manifest는 x86 표기와 w64 파일명이 불일치하고 공급자 최신 안내보다 오래되었습니다. 보안·해시·인증서 경고를 무시하지 마세요.',
    }


def format_install_guide():
    """Plain Korean text for a selectable, copyable help dialog."""
    guide = get_install_guide()
    return '\n\n'.join(guide['steps'] + [guide['privacy'], guide['winget_note']] +
        [label + '\n' + url for label, url in guide['links']])
