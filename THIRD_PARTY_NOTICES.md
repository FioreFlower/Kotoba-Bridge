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

Wiktionary는 사용자가 선택한 페이지를 외부 브라우저에서 여는 링크 연동이다. 본문이나 사전 데이터셋을 포함하지 않는다. Wikimedia의 CC BY-SA 4.0 정책과 항목별 라이선스/기여자 이력을 확인해야 하며, 향후 재사용 시 표시와 동일조건 공유 의무를 검토한다. https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use

예제 일본어/한국어 3쌍은 이 프로젝트를 위해 작성한 합성 문장이다. 실제 게임 대사·화면·사용자 복습 데이터는 포함하지 않는다. 향후 사용자가 생성한 게임 기록의 권리는 해당 권리자에게 있다.
