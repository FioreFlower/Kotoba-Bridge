# 공개 저장소와 Git 이력

공개 저장소: https://github.com/FioreFlower/Kotoba-Bridge

2026-11-13 GitHub 웹 UI에서 `FioreFlower` 소유의 공개 저장소를 생성한 뒤 연결된 GitHub 앱을 통해 소스 39개를 게시했다. 최초 원격 커밋은 `f6f8b3abffb43ddc37bcf19dd9204cf8740c5d97`이다.

최초 로컬 커밋 `b4ac88dfa883d66af348351ceb5747b6dabada07`과 원격 커밋은 이력이 다르다. 두 커밋의 파일 트리 SHA는 `05dbf3423c260b292289a37038baa062615ffc95`로 동일함을 fetch 후 확인했다. 기존 개발 저장소를 원격에 force push하거나 unrelated histories merge하지 않는다. 이후 작업은 원격 main을 clone하거나 원격 커밋에서 새 브랜치/worktree를 만들어 진행한다.

CLI OAuth는 비공개 저장소·Gist 등 추가 계정 권한을 요청하여 승인하지 않고 취소했다. 게시에는 이미 연결된 GitHub 앱을 사용했으며, CLI 인증이 성공했다는 뜻은 아니다. 비밀번호/토큰을 문서·저장소에 보관하지 않는다.

공개 소스는 `git ls-files` 목록으로 제한했다. 가상환경, toolchain/cache, 바이너리, ZIP, Git bundle, 환경/키 파일, 개인 복습 JSON은 제외했다. 예제 문장과 dummy key는 합성 테스트 데이터이며 실제 게임 화면/대사를 포함하지 않는다. 실제 공개 commit metadata의 작성자 정보는 GitHub 계정 설정을 따른다.

최종 사용자용 설치파일은 별도의 Windows 검증·서명 후 Releases 등에 게시한다. 현재 교차 빌드 코어 exe는 전체 설치본이 아니다. GitHub CI의 Windows runner는 실제 게임·GUI·OCR·installer 검증을 대체하지 않는다.
