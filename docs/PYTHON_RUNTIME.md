# Python 개발·패키지 런타임 (2026-11-13 확인)

기존 CI/패키지는 3.13.17이었다. 사용자 PC의 3.11.9는 3.11 마지막 공식 Windows 설치본이며, 3.11 최신 보안 수정판과 동일하지 않다. 3.13.18도 현재 공식 페이지에서 소스 전용으로 표시되어 3.13.17 설치본만을 최신 보안판이라고 권하지 않는다.

이번 변경은 공식 Windows x64 설치본과 actions/python-versions Windows x64 자산이 확인된 **3.14.10 일반 GIL 빌드**를 CI/패키지 기준으로 고정한다. 3.15가 최신 기능 계열이지만 현재 의존성/패키지 검증 범위를 좁히기 위해 3.14를 사용한다. 버전 숫자만으로 모든 보안 문제가 없음을 보장하지 않으며 후속 보안판을 계속 확인해야 한다.

Pillow 13.0.0의 cp314-cp314-win_amd64 wheel SHA-256은 기존 requirements-lock.txt에 포함된 f7cbb7a64e7ec664775195e4f81923bc8a93d9451b963f844e59118f63147a7a이며 PyPI 메타데이터와 재확인했다. PyInstaller 6.22.3 메타데이터 범위는 Python >=3.8,<3.16이다. mss 10.0.0은 기존 고정 버전을 유지한다. 호환 선언/휠 존재만으로 성공이라 하지 않고 Windows/Linux 회귀 및 Windows 동결/설치/포터블 빌드를 실제 실행한다. Tcl/Tk 버전은 빌드 로그에 기록한다.

개발자는 공식 Tcl/Tk 포함 Python 3.14.10+ x64(3.14 계열)를 설치하고 setup_windows.cmd를 실행한다. 이미 .venv가 다른 Python 계열이면 자동 삭제/혼합하지 않고 .venv-backup 등으로 직접 이름을 바꾼 뒤 새로 만들도록 안내한다. 설정·API 키·복습 데이터는 .venv와 별도이며 이전 환경도 임의 삭제하지 않는다. run_windows.cmd는 오래된 환경으로 조용히 실행하지 않는다. 이 안내는 개발 소스용이며 일반 사용자는 Python 설치가 필요 없는 검증된 앱 배포본을 사용한다.

Python 설치 자체는 미서명 Kotoba EXE의 Smart App Control 차단을 해결하지 않는다. 보안 기능 해제·인증서 검증 해제·키 읽기·유료 API 시험을 하지 않는다. 사용자 Windows PC에 설치하거나 가상환경을 변경한 것은 아니다. 최신 CI 결과는 해당 커밋의 Actions에서 확인한다.

공식 출처:
- https://www.python.org/downloads/release/python-3119/
- https://www.python.org/downloads/release/python-31318/
- https://www.python.org/downloads/release/python-31410/
- https://www.python.org/downloads/windows/
- https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json
- https://pypi.org/pypi/Pillow/13.0.0/json
- https://pypi.org/pypi/pyinstaller/6.22.3/json
