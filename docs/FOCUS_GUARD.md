# 시작 포커스 정지 조사

사용자 보고: 0.3 포터블에서 게임 번역 시작을 두 차례 시도했으나 '게임 창 포커스/위치 변경'으로 중지. 실제 API 요청 여부/번역 성공은 미확인. 키·대사·게임 화면을 수집하지 않았고 보안 설정을 바꾸지 않았다.

확인한 코드 순서: 시작 안내는 3초 대기지만 대상 창은 350ms 후 연결했다. 자막은 클릭 통과/비활성 스타일을 다시 설정하기 전에 deiconify했다. 이는 가능한 원인이며 사용자의 Windows에서 원인 확정한 것은 아니다.

수정: 컨트롤 최소화 후 최대 15초 동안 캡처/번역 없이 전경 창과 영역 대상 일치를 기다린다. 자막 스타일을 표시 전에 설정하고, 표시 뒤 다시 전경 일치가 0.6초 이상 유지돼야 실행한다. 한 번 선택한 대상은 기다리는 동안 다른 창으로 자동 재연결하지 않는다. 취소/세대 변경/시간 초과는 캡처 없이 종료한다. 표시 직전/직후 foreground HWND는 진단용 메모리에만 보관하며 제목/화면/키를 기록하지 않는다.

대상은 HWND·프로세스 ID·GetWindowRect 사각형을 함께 고정한다. 영역 전체 포함과 중심점 대상, 전경 일치, 창 위치/크기/프로세스 변경을 계속 검사한다. 앱 자신의 창은 대상이 될 수 없다. OCR 전, API 전, 응답 후의 보호는 유지한다. 검사 직후 실제 화면이 바뀌는 경합이나 모든 작은 겹침 창까지 완전히 탐지한다고 보장하지 않는다. 보호를 끄거나 포커스를 강제로 빼앗지 않는다.

Microsoft 공식 문서상 SetWindowPos는 SWP_NOACTIVATE가 없으면 활성화할 수 있다. GetWindowRect에는 DPI 가상화/보이지 않는 테두리 영향이 있으며 DWM 프레임 사각형과 좌표계를 무조건 혼합하지 않는다. 실제 게임/DPI별 전경 변화·오버레이 이동 검증은 추가 필요하다.
- https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setwindowpos
- https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-getwindowrect
- https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-windowfrompoint

합성 회귀 검사: 전경 불일치 대기 시 캡처 없음, 최초 대상 고정, 안정 후 시작, 시간 초과/이전 세대 무효화, 같은 HWND의 위치/PID 변경 차단, 자막 스타일→표시 순서. Windows 실제 게임 성공이나 실제 API 과금 여부 검증을 의미하지 않는다.
