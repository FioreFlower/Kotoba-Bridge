# OCR 포함 Windows 배포 후보

이 경로는 사용자가 Python, Go, Tesseract 또는 언어팩을 따로 설치하지 않는 것을 목표로 합니다. 설치형 EXE와 압축해제형 ZIP에 앱 런타임, Go 코어, 소스에서 빌드한 Tesseract CLI, 일본어 모델 및 고지문을 포함합니다. 아직 해당 Windows CI 실행이 완료되지 않았다면 **빌드/동작 검증 대기**이며 생성 성공을 주장할 수 없습니다. Windows Server CI 통과도 Windows 10/11 실게임·OCR 품질·저사양 성능 검증을 대신하지 않습니다.

## 고정된 빌드 입력

- [Microsoft vcpkg revision fe8e78fac7df2793f9848ed0d27aa59d9c035998](https://github.com/microsoft/vcpkg/tree/fe8e78fac7df2793f9848ed0d27aa59d9c035998): Tesseract 5.5.4, Leptonica 1.87.0 및 코덱 버전/소스 해시/패치를 고정합니다. 외부 바이너리 캐시는 사용하지 않습니다. vcpkg의 빌드 보조도구 다운로드는 고정 도구 정의의 검증을 따릅니다.
- `packaging/ocr-source/vcpkg.json`에서 Tesseract default features를 끕니다. URL 읽기 curl, libarchive, 학습 도구를 넣지 않습니다. Leptonica 기본 코덱은 유지하므로 PNG 외 JPEG/TIFF/GIF/WebP/OpenJPEG 의존성도 있습니다. 절대 최소 크기라는 주장은 하지 않습니다.
- 사용자 정의 triplet은 x64, release-only, 라이브러리와 MSVC CRT 정적 연결을 요청합니다. OpenMP와 빌드 호스트 CPU 전용 최적화를 끕니다. [Microsoft triplet 설명](https://learn.microsoft.com/en-us/vcpkg/users/triplets)처럼 일부 라이브러리는 정적 요청을 따르지 않을 수 있으므로 파일과 PE import를 추가 검사합니다. 별도 VC 런타임이나 알 수 없는 DLL import 발견 시 빌드를 중단합니다. Windows 기본 시스템 DLL은 OS가 제공합니다.
- [공식 tessdata_fast revision 87416418657359cb625c412a48b6e1d6d41c29bd](https://github.com/tesseract-ocr/tessdata_fast/tree/87416418657359cb625c412a48b6e1d6d41c29bd)의 `jpn.traineddata`만 다운로드합니다. SHA256 `1f5de9236d2e85f5fdf4b3c500f2d4926f8d9449f28f5394472d9e8d83b91b4d` 불일치 시 중단합니다. 모델과 같은 commit의 LICENSE를 포함합니다. 세로 게임 대사 품질은 별도 검증 대상입니다.

이는 **입력과 조리법이 고정된 소스 빌드**이며 바이트 단위 재현성 보증은 아닙니다. runner의 MSVC/Windows SDK 버전이 바뀔 수 있습니다. 실제 vcpkg status, SPDX, 레시피, PE imports, 최종 파일 해시는 패키지 `ocr/provenance`, `ocr/licenses`, `ocr/OCR-SHA256SUMS.txt`에 남깁니다. UB Mannheim 설치기나 DLL은 복사하지 않습니다.

## 타사 저작권 검토

고정 vcpkg port의 `vcpkg.json`, `portfile.cmake` 및 설치된 `share/<port>/copyright`를 기준으로 고지문을 함께 배포합니다. 정적 연결도 고지 의무를 없애지 않습니다.

| 구성요소 | 라이선스/검토 범위 |
|---|---|
| Tesseract / tessdata_fast | Apache-2.0; 소스·모델 라이선스 포함 |
| Leptonica | upstream leptonica-license.txt의 BSD 계열 2조건. vcpkg SPDX 값은 null이라 이를 MIT로 추정하지 않음 |
| libjpeg-turbo | BSD-3-Clause 및 IJG; 설치된 합본 copyright 전체 포함 |
| libpng | libpng-2.0 |
| zlib | Zlib |
| giflib | MIT |
| libwebp | BSD-3-Clause |
| openjpeg | BSD-2-Clause |
| libspng | BSD-2-Clause |
| libtiff | libtiff 라이선스 |
| vcpkg CMake 보조 ports | MIT, 빌드 도구이며 설치된 고지문도 보존 |

[Leptonica 원문](https://github.com/DanBloomberg/leptonica/blob/master/leptonica-license.txt)은 바이너리 배포 자료에 저작권·조건·면책을 포함하도록 합니다. 나머지 정확한 버전별 원문은 [고정된 ports](https://github.com/microsoft/vcpkg/tree/fe8e78fac7df2793f9848ed0d27aa59d9c035998/ports)와 빌드 결과 copyright 파일을 함께 확인합니다. 인가 목록 밖의 새 의존성이나 copyright 누락은 빌드 실패입니다. OCR 의존성 외 Python/Pillow/Tk/Go 고지문은 기존 THIRD_PARTY_LICENSES 수집과 THIRD_PARTY_NOTICES.md를 따릅니다.

## 빌드와 필수 검사

Windows x64 개발 환경(Visual Studio C++ 빌드 도구, Python 3.11, Go, Inno Setup 6) 또는 `Windows installer candidate` CI에서:

```powershell
./packaging/build_ocr.ps1
./packaging/build_windows.ps1
./packaging/smoke_install.ps1
```

새 `.ocr-build` / `.ocr-bundle` 전용 빌드 폴더를 사용합니다. 기존 출력물을 다른 버전과 섞지 않습니다. CI 제한은 45분이며 완료 시간이나 저사양 요구사양을 뜻하지 않습니다.

패키지 smoke는 엔진/모델 존재와 모델 해시, `jpn` 목록, 게임에서 가져오지 않은 합성 일본어 PNG의 실제 Go→OCR 실행 결과를 검사합니다. frozen 앱, 설치한 앱, portable.flag가 있는 별도 포터블 트리 모두 `--self-test --require-ocr` 성공해야 합니다. paid API는 사용하지 않습니다. 설치/제거 smoke도 통과한 경우에만 artifact를 업로드합니다.

- 설치형: `KotobaBridge-Setup-x64.exe`. portable.flag가 없어 사용자 설정은 LOCALAPPDATA에 둡니다.
- 포터블: `KotobaBridge-Portable-x64.zip`. 전체 압축을 쓰기 가능한 폴더에 풀고 EXE를 실행합니다. `portable.flag` 및 `data/` 아래 설정·복습 자료를 사용합니다. EXE 하나만 복사해서 쓰는 방식이 아닙니다. 설치형과 별도 트리로 만들어 플래그가 설치기에 섞이지 않게 합니다.
- `SHA256SUMS.txt`는 EXE와 ZIP 각각의 SHA256입니다. Actions 바깥 ZIP의 digest와 혼동하지 마세요.

초기 실행은 로컬 데모이며 실제 번역은 사용자 키·전송 동의·비용 설정이 필요합니다. 이 패키지는 미서명 개발 후보입니다. Windows 보안 경고 우회, 인증서 확인 해제, 자동 유료 API 호출은 제공하지 않습니다.
