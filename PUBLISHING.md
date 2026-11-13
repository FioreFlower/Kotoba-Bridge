# 공개 저장소 준비와 현재 차단 요인

사용자가 공개 오픈소스 저장소 생성·push를 승인했다. 프로젝트 전용 로컬 Git 저장소를 생성하고 MIT 및 공개 협업 문서를 준비했다.

현재 환경 `gh auth status` 결과: **You are not logged into any GitHub hosts.** 연결된 GitHub 도구도 없어서 실제 계정·생성 권한을 검증할 수 없다. 원격 저장소 생성이나 push는 실행하지 않았고 원격 URL을 만들거나 성공했다고 주장하지 않는다. 인증을 우회하거나 다른 계정을 사용하지 않는다.

인증된 개발 환경에서 공개 범위를 다시 확인한 뒤 다음처럼 게시할 수 있다(실행 예, 이번 작업에서 미실행):

```text
gh auth login
gh repo create kotoba-bridge --public --source=. --remote=origin --push
gh repo view --json nameWithOwner,url,visibility
```

이름이 이미 사용 중이면 새 이름을 지정하고, 기존 저장소를 덮어쓰지 않는다. GitHub 계정 연결/로그인은 사용자가 수행해야 한다. 결제나 유료 서비스 가입은 필요하지 않으며 이번 작업에서 진행하지 않았다.

공개 소스는 `git ls-files` 목록으로 제한된다. `.venv`, toolchain/cache, exe, ZIP, Git bundle, 환경 파일, 키 파일, 사용자가 내보낸 카드 파일은 제외한다. 예제 번역과 오류 테스트의 dummy key 문자열은 실제 인증 정보가 아니다. 이슈에도 실제 화면/키/대사를 올리지 않는다.

최종 사용자용 설치파일은 별도의 Windows 검증·서명 후 GitHub Releases 등에 게시한다. 현재 교차 빌드 코어 exe를 전체 설치본으로 배포하지 않는다.
