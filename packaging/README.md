# Windows 배포 후보 생성

이 폴더는 Windows 빌드 담당자용이다. 최종 사용자는 검증·서명이 완료된 설치본을 받아야 한다. 이번 결과물에 설치 exe는 없다.

1. Windows 10 22H2 x64/Windows 11 x64 빌드 머신, Python 3.11 x64, Go, Inno Setup을 준비한다.
2. 신뢰할 수 있는 Tesseract x64 배포의 실행파일·필수 DLL·jpn 모델·모든 라이선스 고지를 별도 폴더에 모아 해시를 기록하고 악성코드/의존성 검사를 수행한다. 스크립트는 임의 URL에서 OCR을 받지 않는다. LICENSE 하나가 있다는 검사만으로 전체 라이선스 검토가 끝난 것은 아니다.
3. `powershell -File packaging\build_windows.ps1 -TesseractRoot C:\audited-ocr` 실행. 시스템 실행 정책/보안 경고를 우회하지 않는다. 정책이 차단하면 관리자의 정상 승인 경로로 해결한다.
4. dist의 exe 및 bundled OCR을 새 Windows 사용자/VM에서 실행하고 WINDOWS_CHECKLIST.md를 모두 수행한다. 테스트용 번역은 Demo로 진행하며 실 API는 별도 비용 승인 후 검사한다.
5. app 실행파일 서명 후 Inno Setup으로 installer.iss를 컴파일하고 설치본에도 서명한다. 설치/삭제·일본어 언어팩·오프라인 데모·백신 호환성을 검증한다.
6. 설치본·해시·버전별 지원 표·서명 정보를 배포한다. 현재는 이 과정 미실행이며 설치 성공을 주장할 수 없다.

Go 코어 exe, Python/Tk UI runtime, OCR 실행파일/DLL/모델을 포함하는 디렉터리 배포이다. 설치파일 하나로 전달할 수 있어도 내부적으로 단일 실행파일 앱은 아니다. x86/ARM64는 이 레시피에서 제외한다. OCR 폴더 전체 복사는 간단한 시제품 방식이므로 불필요한 파일/개인 설정 유입이 없도록 빌드 입력을 감사해야 한다.
