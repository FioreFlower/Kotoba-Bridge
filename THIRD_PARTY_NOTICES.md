# 타사 구성요소와 데이터 출처

이 저장소의 새 소스는 MIT이다. 아래 구성요소/모델/게임 원문은 프로젝트 MIT로 재라이선스하지 않는다. 최종 설치본을 빌드하는 유지관리자는 실제 포함 버전의 LICENSE/저작권 고지를 복사하고 의존성 전체를 감사해야 한다. Git 소스에는 OCR 실행파일/DLL/모델을 넣지 않는다. 새 실행 패키지는 고정 소스 OCR·모델과 실제 구성요소의 고지/레시피/SPDX/해시를 포함한다. docs/OCR_BUNDLE.md의 라이선스 표와 패키지 ocr/licenses를 함께 확인한다.

| 구성요소 | 역할 | 출처/라이선스 확인 위치 |
|---|---|---|
| Go runtime/stdlib | 코어 빌드·TLS·HTTP | https://go.dev/LICENSE (BSD 계열) |
| CPython | UI 런타임 | https://docs.python.org/3/license.html (PSF 및 동봉 소프트웨어 고지) |
| Tcl/Tk | 네이티브 UI | https://www.tcl-lang.org/software/tcltk/license.html |
| python-mss 10.0.0 | 영역 캡처 | https://github.com/BoboTiG/python-mss/blob/main/LICENSE |
| Pillow 11.3.0 | 이미지 전처리 | https://github.com/python-pillow/Pillow/blob/main/LICENSE |
| Tesseract | 로컬 OCR (미동봉) | https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE (Apache-2.0) |
| jpn traineddata | 일본어 OCR 모델 (미동봉) | https://github.com/tesseract-ocr/tessdata/blob/main/LICENSE |
| UB Mannheim binary dependencies | Windows OCR 배포 후보 | https://github.com/UB-Mannheim/tesseract/wiki — 실제 DLL/모델별 고지 별도 확인 |
| PyInstaller | Windows UI 패키징 | https://pyinstaller.org/en/stable/license.html — GPL 예외의 적용 범위 확인 |
| Inno Setup | 설치 마법사 | https://jrsoftware.org/isinfo.php — 빌드에 사용한 버전의 라이선스 확인 |

DeepL은 외부 서비스이며 코드를 재배포하지 않는다. 사용자 자신의 API 계약/키가 필요하다. https://developers.deepl.com/ . 실제 API를 이번 개발에서 호출하지 않았다.

네이버 일본어사전은 사용자가 확인한 선택어를 외부 브라우저로 검색하는 링크 연동만 제공한다. 사전 내용의 권리는 네이버 및 각 제공처에 있으며 본 앱의 MIT 라이선스 대상이 아니다. 사전 본문·음성·데이터를 수집, 캐시, 번들 또는 재배포하지 않는다. https://ja.dict.naver.com/ (검색 동작은 합성 단어 猫로 확인).

예제 일본어/한국어 3쌍은 이 프로젝트를 위해 작성한 합성 문장이다. 실제 게임 대사·화면·사용자 복습 데이터는 포함하지 않는다. 향후 사용자가 생성한 게임 기록의 권리는 해당 권리자에게 있다.

후속 번들 빌드의 Python은 공식 Windows 다운로드 목록에서 확인한 3.13.17로 CI를 고정한다. [공식 Windows 릴리스](https://www.python.org/downloads/windows/). 이전 3.11.9 기반 후보는 보관된 개발 기록이며 최신 배포 기반으로 사용하지 않는다. 런타임/의존성 전체 취약점 부재를 보증하지 않으며 배포 전 현재 보안 공지 검토가 필요하다.

2026-11-13 공식 PyPI JSON 검사에서 이전 Pillow 11.3.0에 보안 공지가 확인되어 13.0.0으로 갱신했다. 그 시점 Pillow 13.0.0/mss 10.0.0/PyInstaller 6.22.3 응답의 vulnerabilities 목록은 비어 있었다(알려지지 않은 취약점 부재 보증 아님). 배포 런타임의 Pillow/mss 다운로드는 requirements-lock.txt에 고정한 공식 PyPI SHA256을 --require-hashes로 검증한다. [Pillow 메타데이터](https://pypi.org/pypi/Pillow/13.0.0/json), [mss 메타데이터](https://pypi.org/pypi/mss/10.0.0/json).

## 선택 설치 llama.cpp CPU 엔진

공식 b12359 Windows x64 CPU ZIP은 앱 실행 파일에 번들하지 않고 사용자 동의 후 선택 다운로드합니다. llama.cpp MIT 고지는 runtime_catalog.py에 보존하며 설치 시 LICENSE-llama.cpp.txt로 기록합니다. ZIP의 LICENSE-LLVM-OpenMP도 보존합니다. 출처: https://github.com/ggml-org/llama.cpp/releases/tag/b12359 . ZIP 및 52개 개별 파일 크기/SHA-256은 runtime_catalog.py에 고정했습니다. 이는 무결성 확인이며 Authenticode 서명이나 백신 통과 보장이 아닙니다.

## Optional Textractor CLI (not bundled)

The experimental standard-I/O client can invoke the user's separately installed official Textractor 5.2.0 CLI after explicit process selection and consent. Textractor is GPL v3; it is not relicensed by this project's MIT license. No Textractor code, DLL, executable or dictionary content is included in this source tree or app package. Any future combined distribution requires license/source obligations review. Official release, hashes, age, runtime requirements and security limitations: [HOOK_CLI.md](docs/HOOK_CLI.md).
