## 0.2 후속 입력/설치 안내 검증

Linux Python 64개 중 61개 통과, 실제 Tk 표시 환경이 없는 GUI 3개는 제외. 추가 검사: 수동 원문 동의 누락/작업 중 전송 차단, 정확한 원문 1회 전송 목업, 중지 후 늦은 결과 폐기, 오류 자동 재시도 없음, 후보 세대/개수/이벤트/문자 한도, 무자동선택, 설치 안내 무네트워크/무프로세스. 실제 유료 API·외부 WebSocket·게임 주입은 호출하지 않았다. Windows CI 후속 결과는 해당 draft PR의 Actions에서 확인한다. 아래 설치본 해시는 이전 0.2 후보의 기록이다.

## 0.2 Windows CI 설치 후보 검증

[실행 43420625994](https://github.com/FioreFlower/Kotoba-Bridge/actions/runs/43420625994)에서 Windows Server 2025 x64 / Python 3.11.9 / Go 1.27.4로 Go 테스트, Python 45개(위젯 생성 2개 포함), PyInstaller 동결 앱 self-test, Inno Setup 설치본 생성, 설치 후 오프라인 데모 self-test와 제거가 모두 통과했다. 빌드 대상은 PR 가상 merge 2de08f2f48fc62c09a31b842c8a804cf974fed7c, 소스 head 53c028979010d30cd3e453a1786bf3009e83422c이다. 이후 변경은 문서뿐이다.

설치 EXE SHA256: `eb8c873c4d90a813d1eed72476d9ba6bfabbd34ef06b1be96ae037ac696dbc97`. 미서명 개발 후보이며 OCR 엔진/모델은 미포함. 다운로드한 artifact와 내부 설치본 체크섬, 두 self-test 보고서를 확인했다. Windows 10/11 장비의 실제 게임·화면 캡처·클릭 통과·DPI·일본어 OCR·API 연결·성능은 여전히 미검증이다. 서명·의존성 취약점 전수 감사와 일반 사용자 릴리스는 완료하지 않았다.

## 0.2 개발 브랜치 검증 (Linux, 2026-11-13)

Python 45개 중 43개 통과, GUI 2개는 DISPLAY 없음으로 건너뜀. Go 18개 테스트와 go vet 통과. 앱 오프라인 self-test에서 코어 0.2.0, 데모 번역, Python 의존성 확인. 유료 API 호출 없음. 일본어 OCR 모델·Windows 게임·클릭 통과·DPI·저사양 성능은 미검증. Windows CI 및 설치 후보 결과는 PR에서 별도 확인하며 CI의 오프라인 검사는 게임 인수 검사를 대체하지 않음.

이하 기록은 0.1 당시 결과입니다.

# 검증 보고 — 2026-11-13

최종 대상: Windows 10 22H2 x64 / Windows 11 x64. **이번 실행 환경은 Linux이며 Windows 실기 테스트는 0회이다.**

## 실제 수행한 검증

- Linux Python 3.12 가상환경: mss 10.0.0, Pillow 11.3.0 설치/import 성공. 이 항목은 초기 로컬 검증 기록이다. 이후 GitHub CI 결과는 아래 별도로 구분한다.
- Python unittest **26개 통과**: 기본 로직 12, worker 취소/늦은 결과/포커스 mock 5, 학습 JSON/삭제/URL 4, 실제 Go 자식 IPC 5.
- ResourceWarning을 오류로 취급해 재실행, 자식 프로세스 종료/회수 문제 수정 후 26개 통과.
- Go core **8개 테스트 통과**: 안정화, 문맥/캐시/사용량, 모드 전환 시 한도 보존, HTTP payload와 오류/잘못된 응답, 입력 길이 검사, 프로토콜, 잘못된 OCR 이미지. HTTP는 가짜 transport 사용.
- Go 1.27.4 공식 toolchain을 SHA256 검증 후 사용, Linux 및 Windows amd64 코어 빌드 성공. Windows 바이너리는 교차 컴파일 결과일 뿐 실행 성공이 아니다.
- app/bridge/core/study/study_ui Python 문법 컴파일 통과.
- 실제 유료 번역 API 호출 **0회**. 사용자의 실제 API 키 입력·저장·전송 없음.
- 공개 소스에는 합성 예제만 사용. 실제 게임 화면/대사, 사용자 학습 데이터는 수집하지 않음.

명령:

```text
python -W error::ResourceWarning -m unittest discover -s tests -v
python -m py_compile app.py bridge.py core.py study.py study_ui.py
cd go-core
go test ./...
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -buildvcs=false -trimpath -o kotoba-core.exe .
```

## 미검증 / 미완성

| 항목 | 상태 |
|---|---|
| Windows UI 실행·클릭 통과·DPI·다중 모니터·포커스 API | 미검증 |
| 실제 게임 화면 캡처→일본어 OCR→번역 종단간 | 미검증 |
| Linux GUI 데모 창 표시 | DISPLAY 없음으로 미실행 |
| 일본어 OCR 정확도·루비·장식 글꼴 | 로컬 Tesseract에는 eng/osd만 있어 미실행 |
| 실제 DeepL 응답/번역 품질/과금/TLS 서버 접속 | 호출하지 않음 |
| Windows 설치/삭제/서명·보안 제품 호환성 | 레시피만 작성, 미실행 |
| 비개발자용 설치파일 하나 배포 | 완성 설치 exe 미제공 |
| 저사양 CPU/RAM/게임 영향 | 실측 없음. 목표·계획만 작성 |
| GitHub Actions | 실행 #2: Ubuntu/Windows 모두 성공. 초기 인코딩 오류와 수정 내역은 아래 참조 |
| GitHub 공개 저장소 | 공개 게시 완료: 초기 원격 f6f8b3abffb43ddc37bcf19dd9204cf8740c5d97 |

Go와 Python 테스트 통과는 Windows 게임 호환성·GUI 품질의 증거가 아니다. 기본 테스트는 결제를 발생시키지 않으며 Windows 수동 체크리스트 통과와 별도의 사용자 승인 API 테스트가 필요하다.

## 공개 후 CI 확인

최초 원격 커밋 `f6f8b3abffb43ddc37bcf19dd9204cf8740c5d97`의 [Actions 실행 #1](https://github.com/FioreFlower/Kotoba-Bridge/actions/runs/43417532110)을 확인했다.

- `ubuntu-latest`: 전체 job 성공.
- `windows-latest`: Go 테스트, Python 의존성 설치, IPC 코어 빌드 성공. Python 26개 중 25개 성공, `test_roundtrip_and_delete` 1개 오류.
- 원인: 테스트가 UTF-8 JSON을 `Path.read_text()`의 Windows 기본 CP1252로 읽어 `UnicodeDecodeError` 발생. `StudyStore.export`는 UTF-8로 명시 저장하고 실제 import는 bytes JSON을 읽으므로 production 저장/읽기 코드의 오류로 확인된 것은 아니다.
- 수정: 테스트의 읽기/fixture 쓰기에 `encoding='utf-8'`를 명시. Linux에서 수정 후 전체 26개 재통과. 수정 커밋 `47b08f2aad876dedea6ef5a3737b1a5f37f05b5f`의 [Actions 실행 #2](https://github.com/FioreFlower/Kotoba-Bridge/actions/runs/43418219308)에서 Ubuntu/Windows job 모두 성공했다. 각 플랫폼의 Go 테스트, Python 테스트, IPC core 빌드와 최종 Go 빌드가 통과했다.
- Actions 경고: 외부 Go 모듈이 없어 go.sum cache 복원 경고, Node 20 기반 action 버전의 폐기 예정 경고가 있었다. 초기 실패의 원인은 이 경고가 아닌 위 테스트 인코딩이다.

Windows CI의 mock/IPC 테스트는 Windows 게임·GUI·OCR·설치본 실기 검증이 아니다. 해당 미검증 항목은 그대로 유지한다.
