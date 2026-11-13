# API 키 보관 · 0.3 후보

키 입력 → Free/Pro 선택 → **암호화 저장 / 교체**. 입력란은 항상 마스킹하며 저장 후 비웁니다. 재실행 시 저장 상태와 계정 종류를 읽지만 키를 입력란에 복원하지 않습니다. 전송 동의는 매번 새로 필요합니다. 저장 없이 시작하면 메모리에서만 사용하며, 저장 버튼은 API 연결/유효성/요금을 검사하지 않습니다. 오프라인 데모는 저장 키를 configure로 보내지 않습니다.

설치형은 `%LOCALAPPDATA%/KotobaBridge/deepl-key.dpapi`, 포터블은 실행 파일 옆 `data/deepl-key.dpapi`에 저장합니다. 영역/엔진 settings.json과 분리합니다. 파일 형식은 고정 magic/version + Windows DPAPI 암호문입니다. Free/Pro 종류도 키와 함께 암호화됩니다. CRYPTPROTECT_UI_FORBIDDEN을 사용하고 CRYPTPROTECT_LOCAL_MACHINE은 사용하지 않습니다. Python 표준 ctypes와 Windows crypt32/kernel32를 쓰며 추가 암호 라이브러리·서버·마스터 비밀번호는 없습니다.

정상 저장은 암호화 후 암호문만 임시 파일에 쓰고 flush/fsync 후 원자적으로 교체합니다. 실패하면 평문으로 대체하지 않으며 이전 저장 파일을 유지합니다. 복호화/형식/권한 오류는 키나 원본 예외 없이 안내합니다. 새로운 키가 명시적으로 입력되지 않은 상태에서 저장 파일 복호화가 실패하면 기존 코어 키로 몰래 우회하지 않습니다. `API 키 지우기`는 현재 저장 파일, 입력란, 코어 키를 제거합니다. 파일 삭제 실패는 성공으로 표시하지 않습니다. 정상 IPC에서는 세션 사용량을 유지합니다. 코어 오류로 강제 종료된 경우 앱 재실행과 마찬가지로 이후 세션 예산은 별도이며 공급자 사용 한도를 확인해야 합니다.

## 이동·삭제의 제한

다른 PC/다른 Windows 계정으로 키를 이동하는 기능은 지원하지 않습니다. 포터블 폴더 복사나 재설치 시 저장 키가 읽히지 않으면 삭제 후 재입력합니다. Microsoft DPAPI의 도메인 로밍 프로필에는 예외가 있으므로 '어떤 경우에도 PC 밖에서는 해독 불가'라고 주장하지 않습니다. 키 파일이나 폴더 공유를 피하세요. 삭제는 현재 파일만 대상으로 하며 복사본·백업·SSD의 물리적 소거를 보장하지 않습니다. 노출이 의심되면 공급자에서 키를 폐기/재발급합니다.

DPAPI는 디스크 보관 보호입니다. 같은 사용자로 실행되는 악성 코드, 관리자/디버거, OS 계정 탈취, 메모리·크래시 덤프는 방어 범위 밖입니다. 암호화 API 버퍼는 지운 뒤 LocalFree하지만 Python/Go의 불변 문자열·JSON 복사본을 완전히 영점화한다고 보장하지 않습니다. UI→직접 실행한 자식 코어의 stdin configure에는 사용 시 평문 키가 포함됩니다. 명령줄·환경변수·URL·stdout 응답·stderr 로그에 넣지 않으며 IPC 서버나 TCP listener를 열지 않습니다.

## 평문 설정 처리

이전 공식 버전은 키를 저장하지 않았습니다. 별도 수정본의 settings.json 최상위 `key`, `api_key`, `deepl_key`, `deepl_api_key`, `auth_key`(대소문자·밑줄/하이픈 변형 포함)를 발견하면 자동으로 가져오거나 사용하지 않습니다. 유효한 영역/엔진 설정만 원자적으로 다시 쓰고, 평문 백업 파일은 만들지 않습니다. 사용자는 해당 키를 폐기/재발급하고 새 키를 입력해 저장해야 합니다. 손상/알 수 없는 구조/쓰기 실패는 키 사용을 차단하고 설정 삭제 후 재입력을 안내합니다. 임의 파일·다른 앱·과거 백업 전체를 검색하거나 지우지는 않습니다.

## 검증과 근거

테스트는 합성 키만 사용합니다. Linux는 저장 제어/오류/마이그레이션/비노출을 테스트하고 실제 DPAPI는 실행하지 못합니다. Windows CI에는 실제 DPAPI 저장→별도 프로세스 복호화→변조 거부→삭제 테스트, 동결 앱·설치형·포터블 self-test를 추가했습니다. 성공 여부는 해당 커밋의 Actions 결과로 판단합니다. 다른 Windows 계정/다른 PC/도메인 로밍 프로필 인수 검사는 미수행입니다.

- https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata
- https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata
- https://learn.microsoft.com/en-us/windows/win32/seccrypto/example-c-program-using-cryptprotectdata
