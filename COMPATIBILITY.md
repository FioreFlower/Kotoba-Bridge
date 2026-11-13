# 최종 대상과 기술 선택

사용자의 최종 변경을 반영해 **Windows 10 22H2 (build 19045) x64 및 Windows 11 x64**를 1차 개발 대상으로 정한다. Windows 7/8.0/8.1, x86, ARM64는 이번 배포 범위에서 제외한다. 이 범위는 설계 목표이며 실기 통과 목록이 아니다. Windows 전체가 현재 미검증이다.

Windows 10 일반 Home/Pro 지원은 2025-10-14 종료되었다. 지원되는 Windows 11을 우선 권장하며, Windows 10 사용자는 해당 장치의 보안 업데이트/ESU 적용 상태를 별도로 확인해야 한다. 이 앱의 OS 목표가 OS 보안 지원을 연장하지 않는다.
- https://learn.microsoft.com/en-us/lifecycle/products/windows-10-home-and-pro

## Go / C# / 현재 Python 비교와 결정

| 선택 | 장점 | 비용/한계 | 이번 결정 |
|---|---|---|---|
| Go 코어 + 별도 native UI | Go 자체 코드의 컴파일 배포, 관리 런타임 설치 부담 감소 가능 | 텍스트 선택, DPI, 클릭 통과, Win32 GUI binding 유지보수 필요. cgo/외부 OCR 실행파일·DLL·모델은 별도. 메모리 우위 실측 안 됨 | **최종 선택: Go 코어 구현, UI는 아래 Tk 사용** |
| C# WinForms + .NET | Windows 텍스트 컨트롤/설정 마법사/접근성 개발에 유리 | 런타임 동봉 또는 설치, OCR 의존성은 남음. 배포 크기·메모리 실측 필요 | 장기 Windows 전용 제품의 유력 대안, 미구현 |
| Python + Tk + Tesseract | 완성된 기능 시제품, 분리된 adapter/로직 테스트, GUI 기본 제공 | interpreter/Tk/OCR 패키징 필요, pip 소스 설치는 비개발자에 불편 | **UI 구현에 사용**, Go 코어와 함께 Windows installer 레시피 제공 |

Go의 장점을 부정하지 않지만 단순 언어 교체만으로 저사양·단일파일·Windows 검증 문제가 해결되지는 않는다. 사용자의 Go 코어 제안을 반영해 OCR·안정화·번역·한도를 Go로 이전하고 선택/학습 UI는 Tk로 보존했다. 패키징·성능 실측으로 이 경로의 출시 가능성을 판단한다. 성능 목표 미달이면 같은 상태/전송 정책을 C# 또는 Go 네이티브 UI로 이식한다. Go 구현물과 Windows x64 교차 빌드 코어는 이 ZIP에 있다. Windows UI 설치본은 미생성이다.

Go 공식 Windows 지원 문서도 버전별 OS 하한을 구분한다: https://go.dev/wiki/MinimumRequirements . Go runtime, GUI binding, OCR native dependency 각각을 평가해야 한다.

## 제공 상태

- 소스/테스트/오프라인 데모/설정 스크립트 제공.
- Windows x64 PyInstaller 디렉터리 패키지 + OCR 동봉 + Inno Setup 사용자별 설치 레시피 제공 (`packaging/`). Windows 빌드·설치·서명은 미실행.
- 최종 사용자가 Python/pip/Tesseract를 직접 설치할 필요 없는 설치본이 목표다. 이번 ZIP의 소스 실행 경로는 이를 아직 충족하지 못한다.
- 저사양 수치·최소 RAM/CPU 보장은 실측 전에는 하지 않는다. 아래 실측 계획은 유지한다.

---

# 과거 Windows 7 요구 검토 (보존 참고)

**후속 사용자 결정으로 Windows 7/8 지원은 요구 범위에서 제외되었다. 아래는 그 판단 근거이며 현재 출시 조건은 앞 절이 우선한다.** Windows 7/8.0/8.1/10/11 모두 실기 미검증이다. 현재 Python 3.11 + requirements.txt 경로는 Windows 10/11을 대상으로 작성했으며 Win7에는 적용하지 않는다. 새 필수 조건의 충족을 선언하지 않는다.

## 공식 근거와 OS 범위

| 후보 | 공식 확인 | 판단 |
|---|---|---|
| 최신 Electron | Electron 23부터 Win7/8/8.1 지원 종료 | 제외. 구버전 Chromium 고정도 장기 보안 유지 대안 아님 |
| 현재 Python 3.11 시제품 | Python 문서는 Win7 필요 시 3.8 안내 | Win7 지원으로 배포 불가 |
| Python 3.8 실험 브랜치 | Win7용 런타임 계열, 2024-10-07 지원 종료; x86/x64 설치본 존재 | 코드·의존성·TLS의 별도 검증 필요. 구버전 패키지를 임의 고정해 지원 주장하지 않음 |
| C# WinForms + .NET Framework 4.8 | Windows 7 SP1, 8.1 등에 설치 가능. 8.0은 해당하지 않음 | 7 SP1/8.1 이상 별도 경량 클라이언트 후보, 미구현 |
| WinForms + 더 낮은 .NET 대상 | 공식 버전 표에 4.6은 Windows 8 구간을 포함 | Windows 8.0까지 위한 legacy 브랜치 후보이나 해당 런타임 지원 종료·TLS/보안 유지 문제가 남음 |
| C++ Win32 + GDI + 로컬 OCR | 관리 런타임 의존성 감소 가능 | 구형 OS용 toolset/네이티브 의존성/보안 업데이트를 직접 책임지는 별도 제품 개발 필요. 현재 미구현 |

Windows 7 RTM과 SP1은 동일한 지원 범위가 아니다. .NET 4.8 경로는 SP1 전제이며, '7 이상 전부'를 만족하지 않는다. 8.0을 제외하려면 요구 변경 합의가 필요하다. 지금은 임의로 제외하고 완료 처리하지 않는다.

공식 출처:
- https://docs.python.org/3/using/windows.html (Supported Windows versions)
- https://www.python.org/downloads/release/python-387/ (Python 3.8 EOL)
- https://www.python.org/downloads/windows/ (설치본 아키텍처)
- https://electronjs.org/blog/windows-7-to-8-1-deprecation-notice
- https://learn.microsoft.com/en-us/dotnet/framework/get-started/system-requirements
- https://learn.microsoft.com/en-us/dotnet/framework/migration-guide/versions-and-dependencies

## OCR·32/64비트·배포

Tesseract 공식 프로젝트는 Windows 설치를 제3자 배포처로 안내한다. UB Mannheim의 현재 설치본은 x64이며 2023-04-01부터 32비트 설치본 미제공을 명시한다. 오래된 x86 설치본이 존재한다는 사실만으로 현재 안전성, Win7 호환성, 일본어 품질을 보장하지 않는다. 최신 x64 설치본의 Windows 7 실행도 확인하지 못했다.

Win7 x86과 x64 각각의 네이티브 OCR, C/C++ 런타임, 일본어 모델을 별도 조합으로 시험해야 한다. x86 OS는 x64 OCR을 실행할 수 없다. x64 OS에서 x86 앱과 외부 OCR 프로세스를 사용하는 설계는 가능하지만 실제 실행파일과 DLL의 호환성 검증이 필요하다. Python wheel의 Python 버전·비트수와 OS 최소 버전도 별도 확인 대상이다.

설치본은 개발자 Windows 빌드 머신에서 생성하고 서명/해시/라이선스 고지를 포함해야 한다. PyInstaller는 크로스 컴파일러가 아니며 Linux에서 Windows exe를 만들었다고 주장할 수 없다. 5.13 문서도 Windows 8 이상을 명시하므로 무심코 PyInstaller 버전만 낮춰 Win7 보장이라고 쓰지 않는다.

- https://tesseract-ocr.github.io/tessdoc/Downloads.html
- https://github.com/UB-Mannheim/tesseract/wiki
- https://www.pyinstaller.org/
- https://pyinstaller.org/en/v5.13.0/requirements.html

## TLS 및 지원 종료 OS 위험

앱은 기본 신뢰 저장소로 인증서·호스트 이름을 검증하고 TLS 1.2 이상만 요청한다. 과거 Python 단독 구현의 ssl은 OpenSSL을 사용했고, 최종 Go 코어는 Go 표준 crypto/tls와 시스템 신뢰 루트를 사용한다. 아래 Python 관련 설명은 초기 후보 검토 기록이며 최종 경로의 TLS 실증을 뜻하지 않는다. OS가 TLS 옵션을 지원한다는 사실과 실제 API TLS 접속 성공은 다르다. 배포 런타임의 OpenSSL 버전, 신뢰 루트 인증서, OS 시계, DNS/SNI, 서버 암호군, 프록시 정책을 Win7 x86/x64에서 확인해야 한다. .NET 후보는 Schannel/OS 설정과 런타임별 TLS 기본값까지 확인해야 한다.

DeepL 문서는 HTTPS API를 제공하지만 이번 작업에서 Windows 7 TLS 협상 성공 또는 서버가 허용하는 최소 TLS 버전을 실측하지 않았다. 앱 자체 최소값을 TLS 1.2로 설정했으며 공급자의 지원 보증이라고 표현하지 않는다. 인증서 오류 시 중지하고 공식 업데이트/지원되는 OS로 해결한다. 검증 해제, 임의 인증서 신뢰, 보안 경고 우회는 없다. 실제 번역 API 호출도 하지 않았다.

Win7 일반 보안 지원은 2020-01-14 종료되었다. 구형 OS와 런타임은 알려진/미해결 취약점으로 API 키와 화면 텍스트를 위험에 노출할 수 있다. 온라인 API 키를 저장하는 제품으로 정식 권장하려면 별도 보안 유지 방안이 필요하다. 지원되는 OS로 업그레이드하거나 게임 PC와 별도의 지원되는 기기에 표시·번역을 분리하는 대안이 있으나 후자는 캡처 전달 장치/소프트웨어와 개인정보 설계를 추가해야 하며 현재 구현하지 않았다.

- https://docs.python.org/3/library/ssl.html
- https://developers.deepl.com/api-reference/translate/request-translation
- https://learn.microsoft.com/en-us/troubleshoot/windows-client/windows-7-eos-faq/windows-7-end-support-faq-general

## 쉬운 초기 설정과 출시 게이트

개발용 `setup_windows.cmd`는 Python 3.14.10 이상(3.14 계열)이 설치된 Windows 10/11에서 가상환경·패키지 설치·데모 실행을 묶는다. 실제 설치 마법사나 Tesseract 자동 설치기는 아니다. 일반 사용자는 이 개발 경로 대신 OCR/모델/런타임 포함 설치형 또는 포터블 후보를 사용한다. 해당 CI 성공 여부와 실제 게임 미검증 범위는 TEST_REPORT를 따른다.

정식 배포 계획: OS/SP/비트수 자동 감지 → 지원 표 확인 → 서명된 런타임/OCR/일본어 모델 포함 설치 또는 명시적 다운로드 → 오프라인 예제 OCR 검사 → 마우스 영역 지정 → 원문 미리보기 → 키/전송 안내 → 작은 문자 한도로 시작. 업데이트는 서명 검증, 제거는 학습 자료 보존/삭제 선택, API 키는 0.3 후보에서 선택적 Windows 사용자 범위 DPAPI 보관으로 구현. 0.2에서는 드래그 지정·로컬 OCR 미리보기·초기 설정 검사와 설치 후보 빌드/검사 CI를 구현했다. 후속 OCR 포함 빌드와 포터블 ZIP을 구현했다. 빌드 성공·실행 범위는 TEST_REPORT와 Actions가 기준이다. 서명·자동 업데이트·Windows 게임 실기 검증은 미완료다.

## 저사양 실측 계획 (수치는 목표이며 검증된 최소 사양 아님)

- 기준 후보: 2코어 CPU, RAM 2GB/4GB, HDD/SSD, GPU 가속 없음. Win7 SP1 x86/x64, 8.0 x86/x64, 8.1 x64, 지원되는 Windows 10/11을 구분한다.
- 1280×720 / 1920×1080 게임에서 800×180 대사 영역, 가로쓰기 100개 문장, 30분 반복. 게임 단독 대비 게임 프레임 시간, 앱+OCR peak working set, CPU 평균/p95, 캡처/OCR/API/전체 지연을 따로 기록한다.
- 목표 예: 앱+OCR 300MB 이하, 평균 CPU 10% 이하(해당 CPU 기준), 로컬 OCR p95 1.5초 이하. 충족하지 못하면 ROI/배율/주기를 조정하며 목표를 최소 사양으로 광고하지 않는다.
- 현 구현은 단일 worker, 1초 검사 주기, OCR 처리 이미지를 최대 약 200만 픽셀로 제한, OMP_THREAD_LIMIT 기본 1, 메모리 기록/캐시 개수 제한을 적용했다. CPU/메모리 수치는 실측하지 않았다.
- 게임 대사가 그대로여도 OCR을 반복하므로 저사양 최적화 여지가 있다. 다음 단계는 픽셀 변화 감지로 동일 프레임 OCR 건너뛰기와 지속 OCR 엔진이다.

Windows 장비/VM, 구형 의존성의 검증된 빌드, 서명 가능한 Windows 패키징 환경이 남은 차단 요인이다. 이 제한은 설치 완료/지원 완료로 대체할 수 없다.
