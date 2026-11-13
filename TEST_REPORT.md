# 검증 보고 — 2026-11-13

최종 대상: Windows 10 22H2 x64 / Windows 11 x64. **이번 실행 환경은 Linux이며 Windows 실기 테스트는 0회이다.**

## 실제 수행한 검증

- Linux Python 3.12 가상환경: mss 10.0.0, Pillow 11.3.0 설치/import 성공. 문서의 Windows Python 3.11 환경은 미실행.
- Python unittest **26개 통과**: 기본 로직 12, worker 취소/늦은 결과/포커스 mock 5, 학습 JSON/삭제/URL 4, 실제 Go 자식 IPC 5.
- ResourceWarning을 오류로 취급해 재실행, 자식 프로세스 종료/회수 문제 수정 후 26개 통과.
- Go core **8개 테스트 통과**: 안정화, 문맥/캐시/사용량, 모드 전환 시 한도 보존, HTTP payload와 오류/응답 제한, 프로토콜, 잘못된 OCR 이미지. HTTP는 가짜 transport 사용.
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
| GitHub Actions | workflow만 작성, 원격 실행 안 함 |
| GitHub 공개 저장소 | gh 인증 계정 없음으로 생성·push 불가 |

Go와 Python 테스트 통과는 Windows 게임 호환성·GUI 품질의 증거가 아니다. 기본 테스트는 결제를 발생시키지 않으며 Windows 수동 체크리스트 통과와 별도의 사용자 승인 API 테스트가 필요하다.
