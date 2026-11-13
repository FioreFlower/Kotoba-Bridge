# Go 코어 + 네이티브 UI

## 책임 경계

- Python/Tk UI: 설정, 전송 동의, MSS 영역 캡처·전처리, Windows 포커스/창 검사, 원문 위/번역 아래 자막, 클릭 통과 스타일, 선택 학습/기록/복습 JSON, 외부 사전 확인.
- Go 코어: Tesseract 프로세스 실행과 timeout, OCR 결과 안정화/중복 억제, DeepL adapter, 문맥/캐시, 요청·문자 예산, 안전한 오류. 기본 데모는 고정 번역으로 외부 통신하지 않는다.
- Tesseract: 별도 네이티브 exe/DLL/일본어 모델. Go 바이너리 자체가 앱 전체를 대체하지 않는다.

C# WinForms UI로 갈아 끼울 수 있도록 JSON 규약을 분리했다. 이번 버전은 Tk이며 C# UI는 구현하지 않았다. Windows 네이티브 창 API는 ctypes로 호출한다. Go의 언어 특성만으로 전체 메모리·성능을 보장하지 않는다.

## IPC v1

UI가 같은 설치 폴더의 `kotoba-core.exe`를 shell 없이 자식으로 실행한다. stdin/stdout의 UTF-8 JSON 한 줄을 한 요청/응답으로 사용한다. HTTP listener, localhost 포트, named pipe 서버, 외부 실행 명령 입력은 없다. API 키를 명령줄·환경변수·파일로 전달하지 않고 configure 메시지로만 전달한다. 프로세스 메모리/디버거 접근권한까지 차단하는 보안 경계는 아니다.

요청 예 (키가 없는 데모):

```json
{"id":1,"version":1,"method":"configure","demo":true,"pro":false,"key":""}
```

응답은 `id`, `version`, `ok`, `result` 또는 안전한 `error`를 포함한다. hello에서 protocol=1 확인, 응답 id/version 매칭, 단일 요청 lock, 크기 제한, 25초 UI 대기 timeout을 둔다. OCR는 6초, 번역은 15초 제한이다. 키/원문 stderr를 출력하지 않고 UI는 코어 stderr도 기록하지 않는다.

주요 method: hello, configure, ocr(image base64 PNG + 선택된 로컬 tesseract 경로), observe(text/reset), translate(text), status, clear, shutdown. 문자열/API 처리 정책은 go-core 소스와 테스트가 최종 기준이다. `core.py`의 기존 Python 번역 구현은 이전 단계의 참조/회귀 테스트용으로 남아 있으며 현재 app.py의 실사용 번역 경로는 GoTranslator이다.

## 실패와 복구

코어 종료, protocol 불일치, 잘못된 응답, timeout은 사용자 오류로 전환하고 자동 재시작/재전송하지 않는다. 특히 timeout 후 서버가 이미 처리했을 수 있어 비용을 자동 반복시키지 않는다. 앱을 재시작하면 프로세스 세션 예산이 초기화된다. 공급자 계정 한도는 별도로 설정한다.

정지 시 UI 세대 번호로 늦은 응답을 폐기한다. IPC는 단일 요청이므로 진행 중 요청 자체를 즉시 취소하는 별도 control channel은 없다. 이미 전송한 API는 멈출 수 없으며 종료 시 child를 종료해도 과금 여부는 달라지지 않는다. 학습 진입은 worker 종료를 기다린 뒤 허용한다.

코어의 번역 응답 후 UI가 포커스와 OCR 원문을 재검사한다. 대사가 달라졌거나 정지한 상태면 화면 표시를 버린다. 이 재검사에는 추가 로컬 OCR 시간만 들고 추가 번역 요청은 하지 않는다. 프레임 검사는 원자적이지 않으므로 마지막 검사 직후 화면 변경의 잔여 경쟁 조건은 있다.

## 패키징 및 업데이트

하나의 설치파일 안에 UI, Go core, Python/Tk runtime, Tesseract와 jpn 모델 및 라이선스를 함께 넣는 onedir 패키징을 계획했다. `packaging/build_windows.ps1`과 `installer.iss`가 빌드 레시피다. 0.2 CI는 UI/코어/런타임을 함께 패키징하고 오프라인 설치·삭제 검사를 수행한다. 성공 여부는 해당 Actions 결과를 확인한다. 후속 빌드는 고정 소스에서 정적 연결한 Tesseract와 검증된 일본어 모델을 포함하고 설치형·포터블에서 OCR self-test를 필수로 한다. 성공 여부는 해당 CI를 기준으로 한다. 서명과 Windows 10/11 게임 인수 검사는 미수행이다.

앱/UI/core를 한 릴리스로 원자적으로 교체하고 프로토콜이 다르면 실행을 거절한다. 현 버전에는 자동 업데이트가 없으며 installer 재설치를 통한 업데이트만 계획한다. 사용자 복습 파일은 앱 설치 폴더가 아닌 사용자가 고른 위치에 저장되어 업데이트/제거와 독립적이다.

교차 빌드된 Go Windows exe는 빌드 성공만 확인할 수 있으며 Windows 실행 성공 증거가 아니다. Python/Tk UI freezing과 Inno installer 빌드는 Windows가 필요하다.
