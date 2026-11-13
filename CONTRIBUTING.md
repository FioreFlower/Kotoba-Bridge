# 기여 안내

Windows 10 22H2 x64/Windows 11 x64 대상 Go core + Tk UI 시제품입니다. Go 코어는 표준 라이브러리만 사용합니다. UI에는 Python 3.11, tkinter, requirements.txt가 필요합니다.

1. 저장소를 fork/clone하고 기능 브랜치를 만듭니다.
2. `cd go-core` → `go test ./...` → `go build -o ../kotoba-core.exe .` (Windows). Linux는 출력명 `../kotoba-core`를 사용합니다.
3. 상위 폴더에서 Python venv 생성, requirements 설치, `python -m unittest discover -s tests -v` 실행.
4. `python app.py`의 오프라인 데모로 확인합니다. 유료 API 테스트는 기본 테스트에 넣지 않습니다.
5. PR에 변경 목적, 테스트 환경/결과, 미검증 Windows 항목, 개인정보/비용 영향, 필요한 protocol 변경을 적습니다.

실제 키·게임 화면·개인 대사·내보낸 복습 파일을 커밋하거나 이슈에 붙이지 마세요. 합성 데이터만 사용합니다. 게임 파일 패치, DLL 주입, 안티치트/DRM 우회, TLS 검증 해제는 프로젝트 범위 밖입니다.

IPC v1 변경은 UI와 코어를 함께 수정하고 버전 불일치 테스트를 추가합니다. 프레임/키를 로그에 넣지 않습니다. 실패한 요청을 자동 재시도하지 않습니다. Windows 검증은 WINDOWS_CHECKLIST.md, 설치본은 packaging/README.md를 따릅니다. 플랫폼 미검증을 통과로 보고하지 않습니다.

코드 기여는 프로젝트 MIT 라이선스에 따라 제공됩니다. 외부 코드를 추가할 때 출처·저작권·라이선스와 모델/데이터 재배포 권한을 THIRD_PARTY_NOTICES.md에 명시합니다.
