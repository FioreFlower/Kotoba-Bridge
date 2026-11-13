# Windows 설치 후보 빌드

기본 결과물은 하나의 **미서명 개발용 설치 파일**이다. 내부에는 Python/Tk UI runtime, Go core exe와 라이선스 고지가 들어가며 Tesseract/일본어 모델은 기본적으로 포함하지 않는다. 앱 설치·데모는 OCR 없이 가능하지만 실제 게임 OCR에는 별도 엔진/언어팩이 필요하다.

## 자동 빌드

GitHub 저장소에서 **Actions → Windows installer candidate → Run workflow → 사용할 브랜치 선택 → Run workflow**로 실행한다. 새 workflow가 기본 브랜치에 아직 없으면 GitHub가 수동 실행 메뉴를 노출하지 않을 수 있다. 먼저 해당 workflow 파일이 기본 브랜치에 등록되어 있어야 하며, UI에서 제공하지 않는 실행 경로를 성공했다고 주장하지 않는다. workflow 파일은 `.github/workflows/build-windows.yml`이다. 관련 소스·테스트·패키징 변경의 `pull_request`에서도 실행하므로 기본 브랜치에 병합하기 전에 설치 후보를 검증할 수 있다. PR 실행은 `contents: read`이며 secrets, `pull_request_target`, 자동 Release 게시를 사용하지 않는다. Windows Server 2025 x64 runner에 Python 3.11 x64, Go를 설정하고 다음을 수행한다.

1. Go/Python 테스트와 IPC core 빌드.
2. PyInstaller onedir UI 패키징, Go core와 런타임 라이선스 고지 복사.
3. frozen `KotobaBridge.exe --self-test --report ...` (화면·API 없이 import/IPC 검사).
4. runner에 이미 설치된 Inno Setup 6으로 설치파일 생성.
5. 일회성 임시 폴더에 무인 설치 → 설치된 앱의 오프라인 self-test → 제거. 이 단계는 자체 빌드 파일을 disposable CI에서 시험하는 절차이며 사용자에게 보안 경고 우회를 요청하지 않는다.
6. SHA256, 빌드 커밋, 두 self-test 보고서와 설치 후보 artifact 보존 (14일).

워크플로는 read-only repository 권한이며 토큰/키가 필요하지 않다. 자동 Release 생성·서명·유료 API 호출은 없다. 성공한 실행이 없으면 설치 후보가 만들어진 것으로 주장하지 않는다. CI runner는 Windows Server이며 Windows 10/11 실제 게임 환경과 다르다.

## 로컬 Windows 빌드

Windows x64, Python 3.11 x64, Go, 공식 Inno Setup 6을 준비한다. 다음 명령은 정상 PowerShell 실행 정책 내에서 실행한다. 정책 우회 옵션을 사용하지 않는다.

```powershell
./packaging/build_windows.ps1
./packaging/smoke_install.ps1
```

`build_windows.ps1 -SkipInstaller`는 frozen 앱까지 만든다. Python 명령이 다르면 `-PythonExe`에 정상 설치한 실행파일 경로를 전달한다. Inno compiler는 PATH 또는 `Program Files (x86)\Inno Setup 6\ISCC.exe`에서 찾고 없으면 중지한다. 무검증 설치파일 자동 다운로드는 없다.

## 선택적 OCR 동봉

기본 경로와 별개로, 출처·해시·네이티브 DLL·모델의 라이선스를 사람이 검토한 OCR 폴더만 `-TesseractRoot C:\audited-ocr`로 전달할 수 있다. 폴더에는 `tesseract.exe`, `tessdata\jpn.traineddata`, `REDISTRIBUTION_REVIEW.md`와 각 저작권/라이선스 고지가 있어야 한다. 검토 문서에는 파일별 출처·버전·해시·재배포 조건을 적는다. 스크립트의 파일 존재 검사는 실제 법적/공급망 검토를 대신하지 않는다. 기본 GitHub workflow는 이 옵션을 사용하지 않으며 OCR 자료를 재배포하지 않는다.

## 릴리스 전 남은 게이트

- 실제 묶인 Python/Tk, Pillow 및 Pillow DLL, MSS, Go, PyInstaller bootloader의 라이선스/고지 확인. `collect_notices.py`는 설치된 패키지의 고지를 모으지만 완전한 법률 검토가 아니다.
- 소스/의존성 감사, 서명 인증서와 사용자 확인 절차, Windows 보안 제품 호환성.
- WINDOWS_CHECKLIST.md의 게임·오버레이·DPI·다중 모니터·OCR·취소 테스트.
- 저사양 CPU/RAM/게임 프레임 영향 측정. 빌드 크기와 설치 성공은 저사양 성능 증거가 아니다.

앱 제거 스크립트는 사용자의 외부 복습 파일·설정을 삭제하지 않는다. installer의 기존 AppId를 유지해 동일 제품 업데이트 경로를 보존한다. 설치 실행 후 자동 앱 시작 체크는 기본 해제되어 있다.

## 공식 확인 자료

- Node24 action 버전 및 입력: https://github.com/actions/checkout , https://github.com/actions/setup-go , https://github.com/actions/setup-python , https://github.com/actions/upload-artifact
- runner 설치 도구: https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md (Inno Setup 6 포함)
- Inno Setup: https://jrsoftware.org/ishelp/

워크플로의 action은 확인된 commit SHA로 고정했고, 외부 Go 모듈이 없으므로 module cache를 껐다. Python 패키지는 버전 고정이며 전체 hash lock/SBOM은 아직 제공하지 않는다.
