> 이 문서는 개발 소스 실행 또는 사용자가 별도 엔진을 선택할 때의 복구 안내입니다. 새 일반 사용자 배포 경로는 OCR/모델 포함 설치형·포터블이며 [OCR_BUNDLE.md](OCR_BUNDLE.md)가 우선합니다.

# Windows OCR 초기 설정

검토일: 2026-11-13. 기존 OCR 미포함 후보와 개발 소스의 별도 엔진 설정을 조사한 기록입니다. OCR 없이 오프라인 데모를 먼저 사용할 수 있습니다. 이 문서는 Windows 설치 실기 검증 완료를 뜻하지 않습니다.

## 직접 설치하고 확인하기

1. [Tesseract 공식 설치 문서](https://tesseract-ocr.github.io/tessdoc/Installation.html)를 열고 Windows 항목의 [UB Mannheim 안내](https://github.com/UB-Mannheim/tesseract/wiki)를 확인합니다. Tesseract 프로젝트가 연결하는 **제3자 Windows 배포본**이며 Kotoba Bridge가 제작하거나 안전성을 보증한 설치파일은 아닙니다.
2. 공급자가 안내하는 64비트 파일의 버전과 출처, Windows 보안 표시를 확인한 뒤 직접 설치합니다. 검토 당시 공급자 wiki는 `5.5.3.20260724`를 안내했습니다. 최신 버전이나 서명 상태가 바뀔 수 있으므로 이 문서의 버전만 믿고 다른 사이트의 동명 파일을 실행하지 마세요. 보안 경고·인증서 검증·해시 검사를 우회하지 마세요.
3. 기본 설치 위치 또는 새 전용 폴더를 사용합니다. 공급자 wiki는 제거할 때 설치 폴더와 하위 자료가 모두 삭제될 수 있다고 경고합니다. 기존 게임·문서·Kotoba Bridge 폴더에 설치하지 마세요.
4. 언어 구성에서 일본어 `Japanese` / `jpn`을 선택합니다. 정확한 구성 화면은 버전마다 다를 수 있고 이번 작업에서 직접 검증하지 않았습니다. 모델 다운로드에는 인터넷 접속이 필요할 수 있습니다.
5. Kotoba Bridge의 OCR 재검사를 실행합니다. 자동 발견이 안 되면 `tesseract.exe`를 선택합니다. 선택 파일은 검사 시 로컬 프로세스로 실행되므로 출처를 먼저 확인하세요.
6. `jpn` 누락이면 설치 프로그램의 언어 구성이나 [공식 tessdata_fast 저장소](https://github.com/tesseract-ocr/tessdata_fast)를 확인합니다. 모델을 직접 추가하는 경우 실제 엔진의 `tessdata` 폴더와 권한을 확인하세요. HTML 페이지를 `.traineddata`로 저장하면 동작하지 않습니다. `--list-langs` 통과만으로 파일 내용이나 인식 정확성을 검증할 수 없습니다. 로컬 OCR 미리보기로 실제 결과를 확인하세요.

화면은 로컬 OCR에만 사용됩니다. 링크를 누르면 브라우저가 사이트에 접속하며, 엔진·모델 다운로드와 번역 API 전송은 별개입니다. 이 안내 헬퍼는 네트워크 접속, 다운로드, 실행, 권한 상승, 설치 또는 모델 교체를 하지 않습니다. 게임 이미지·대사·키를 설치 제공자에 전송하지 않습니다.

## WinGet 검토 결과

확인한 Microsoft 커뮤니티 저장소의 정확한 ID는 `UB-Mannheim.TesseractOCR`입니다. [버전 목록](https://github.com/microsoft/winget-pkgs/tree/master/manifests/u/UB-Mannheim/TesseractOCR)에서 확인한 최신 숫자 버전은 `5.4.0.20240606`으로 공급자 안내보다 오래되었습니다. [해당 설치 manifest](https://github.com/microsoft/winget-pkgs/blob/master/manifests/u/UB-Mannheim/TesseractOCR/5.4.0.20240606/UB-Mannheim.TesseractOCR.installer.yaml)는 다음 정보를 갖습니다.

- 형식 `nullsoft`, 아키텍처 `x86`.
- URL은 UB-Mannheim GitHub release의 `tesseract-ocr-w64-setup-5.4.0.20240606.exe`를 가리킵니다. 아키텍처 표기와 파일명의 불일치를 발견했으며 이 환경에서 실행파일 아키텍처를 직접 검증하지 않았습니다.
- 기록된 SHA256은 `C885FFF6998E0608BA4BB8AB51436E1C6775C2BAFC2559A19B423E18678B60C9`입니다. **manifest에서 읽은 구버전 값이며 다운로드 파일을 직접 해시한 결과가 아닙니다. 최신 5.5.3 파일의 해시가 아닙니다.**
- 일본어 언어팩 선택을 보증하는 옵션이나 별도의 installer switches는 이 manifest에 없습니다.

따라서 MVP는 WinGet 설치 명령 실행 버튼이나 구버전 고정 설치를 제공하지 않습니다. 관리자가 별도로 WinGet을 사용할 경우 먼저 `winget show --id UB-Mannheim.TesseractOCR --exact --source winget`로 현재 선택 결과를 확인해야 합니다. 이것도 사용자가 직접 수행하는 온라인 조회이며 앱은 실행하지 않습니다. Microsoft [install 명령 문서](https://learn.microsoft.com/en-us/windows/package-manager/winget/install)의 exact/source/version/interactive 옵션을 검토했습니다. 자동 약관 수락·silent 설치·hash 무시 옵션은 사용하지 않습니다. manifest의 해시와 실제 파일 일치는 무결성 확인이지 악성코드 부재나 배포 신뢰성 보증이 아닙니다.

## 라이선스와 배포 범위

[Tesseract 엔진 LICENSE](https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE)와 [tessdata_fast LICENSE](https://github.com/tesseract-ocr/tessdata_fast/blob/main/LICENSE)는 Apache-2.0입니다. 모델 저장소는 LSTM용 속도/정확도 절충 모델이며 게임별 품질·저사양 성능은 별도 측정이 필요합니다. UB Mannheim Windows 패키지의 모든 DLL·설치기·모델이 동일 라이선스라는 뜻은 아닙니다. 현재 그 전체 구성물을 다운로드·감사하거나 재배포하지 않았습니다. 향후 번들 전에는 정확한 버전, 파일별 해시, DLL 의존성과 라이선스/고지문, 모델 출처와 재배포 조건을 기록해야 합니다.

## 구현 및 검증

`ocr_install.get_install_guide()`는 단계·링크·전송 설명·WinGet 제한을 독립된 사전으로 반환합니다. `format_install_guide()`는 선택/복사 가능한 도움말 창에 넣을 한국어 문자열을 반환합니다. UI는 사용자가 요청했을 때만 링크를 열어야 합니다. 기존 `onboarding.inspect_engine()`가 로컬 실행과 `jpn` 목록 검사를 담당합니다. 헬퍼 테스트는 네트워크/프로세스/브라우저 호출이 없고, 안내 데이터가 호출 간 오염되지 않는지 확인합니다. Windows 설치 화면·최신 설치파일의 서명·OCR 실기 및 언어팩 설치 성공은 미검증입니다.
