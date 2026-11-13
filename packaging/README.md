# Windows 설치 후보 빌드

기본 결과물은 **미서명 개발용 설치 EXE와 포터블 ZIP**이다. Python/Tk UI runtime, Go core, 소스에서 빌드한 Tesseract와 일본어 모델, 라이선스 고지를 포함한다. 사용자가 런타임이나 OCR을 따로 설치하지 않는 경로다. 정확한 소스·모델 고정값과 의존성 고지는 [OCR_BUNDLE.md](../docs/OCR_BUNDLE.md)를 따른다.

## 자동 빌드

GitHub 저장소에서 **Actions → Windows installer candidate → Run workflow → 사용할 브랜치 선택 → Run workflow**로 실행한다. 새 workflow가 기본 브랜치에 아직 없으면 GitHub가 수동 실행 메뉴를 노출하지 않을 수 있다. 먼저 해당 workflow 파일이 기본 브랜치에 등록되어 있어야 하며, UI에서 제공하지 않는 실행 경로를 성공했다고 주장하지 않는다. workflow 파일은 `.github/workflows/build-windows.yml`이다. 관련 소스·테스트·패키징 변경의 `pull_request`에서도 실행하므로 기본 브랜치에 병합하기 전에 설치 후보를 검증할 수 있다. PR 실행은 `contents: read`이며 secrets, `pull_request_target`, 자동 Release 게시를 사용하지 않는다. Windows Server 2025 x64 runner에 Python 3.11 x64, Go를 설정하고 다음을 수행한다.

1. 고정 vcpkg 소스에서 OCR/코덱 정적 빌드, 일본어 모델 해시와 라이선스 수집, PE 런타임 의존성 검사. Go/Python 테스트와 IPC core 빌드.
2. PyInstaller onedir UI 패키징, Go core와 런타임 라이선스 고지 복사.
3. frozen `KotobaBridge.exe --self-test --require-ocr --report ...` (화면·API 없이 import/IPC 및 합성 일본어 실제 OCR 검사).
4. runner에 이미 설치된 Inno Setup 6으로 설치파일 생성.
5. 일회성 임시 폴더에 무인 설치 → 설치된 앱의 오프라인 self-test → 제거. 이 단계는 자체 빌드 파일을 disposable CI에서 시험하는 절차이며 사용자에게 보안 경고 우회를 요청하지 않는다.
6. 별도 portable.flag 트리를 만들고 포터블 OCR smoke 후 ZIP 생성. SHA256, 빌드 커밋, 세 self-test 보고서와 두 배포 후보 artifact 보존 (14일).

워크플로는 read-only repository 권한이며 토큰/키가 필요하지 않다. 자동 Release 생성·서명·유료 API 호출은 없다. 성공한 실행이 없으면 설치 후보가 만들어진 것으로 주장하지 않는다. CI runner는 Windows Server이며 Windows 10/11 실제 게임 환경과 다르다.

## 로컬 Windows 빌드

Windows x64, Visual Studio C++ 빌드 도구, Python 3.11 x64, Go, 공식 Inno Setup 6을 준비한다. 다음 명령은 정상 PowerShell 실행 정책 내에서 실행한다. 정책 우회 옵션을 사용하지 않는다.

```powershell
./packaging/build_ocr.ps1
./packaging/build_windows.ps1
./packaging/smoke_install.ps1
```

`build_windows.ps1 -SkipInstaller`는 설치 EXE 없이 frozen 앱과 포터블 ZIP을 만든다. Python 명령이 다르면 `-PythonExe`에 정상 설치한 실행파일 경로를 전달한다. Inno compiler는 PATH 또는 `Program Files (x86)\Inno Setup 6\ISCC.exe`에서 찾고 없으면 중지한다. 무검증 설치파일 자동 다운로드는 없다.

## OCR 소스 빌드

기본 `.ocr-bundle` 입력은 `build_ocr.ps1`이 생성한다. UB Mannheim 설치기나 무감사 바이너리를 넣지 않는다. 다른 `-TesseractRoot` 입력을 쓰려면 동일한 출처·버전·해시·라이선스와 DLL 의존성 검토를 먼저 마쳐야 한다. `REDISTRIBUTION_REVIEW.md` 존재만으로 감사를 대신할 수 없다. CI는 고정 소스 빌드 경로만 사용한다.

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
