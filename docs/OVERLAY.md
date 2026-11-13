# 배경만 투명한 Windows 자막 · 0.3 후보

게임 창을 변경하지 않습니다. 일본어/한국어 Tk 텍스트 창은 alpha=1.0을 유지하고 배경색(#17212d)에만 Windows color key를 적용합니다. 그 아래의 별도 장식용 배경 창에만 alpha 0–100%를 적용합니다. 따라서 전체 창 alpha로 글자를 흐리게 만들지 않습니다. color key는 해당 색 픽셀을 완전히 비우고 별도 창의 배경만 게임 화면과 합성합니다. 타이틀 바·선택 강조는 별개이며 사라지지 않을 수 있습니다.

`자막 배경 불투명도` → `배경 설정 저장`으로 설치형/포터블 데이터 폴더의 overlay.json에 허용된 값만 보관합니다. 0%에서도 글자는 그대로이며 `자막 표시 / 위치·배경 복구`는 창을 화면 안 기본 위치로 옮기고 배경을 85%로 되돌립니다. 복구는 캡처를 정지합니다. 변경한 복구값을 다음 실행에도 쓰려면 저장하세요.

장식용 배경은 항상 클릭 통과·비활성화 창입니다. 그 설정이 실패하면 배경을 숨깁니다. 글자 창은 플레이에서 클릭 통과, 학습에서 선택 가능하게 전환합니다. color key로 투명해진 빈 픽셀은 학습 모드에도 클릭을 아래 창으로 넘길 수 있습니다. 글자 위에서 선택을 시작하거나 불투명한 학습 기록 창에서 선택하세요. 창 이동/크기/숨김에 배경 위치·표시를 동기화합니다. 다른 OS나 Windows color key 초기화 실패에는 불투명한 배경을 유지하며 전체 글자 alpha로 대체하지 않습니다.

Windows layered window API와 Tk의 transparentcolor를 이용한 구현 후보입니다. 글자 픽셀의 전역 불투명도는 100%이나 폰트 안티앨리어싱의 색상 키 가장자리/프린지, DPI·크기·Z-order, 게임별 클릭 통과와 독점 전체화면 호환성은 Windows 10/11 실기 미검증입니다. 고품질 per-pixel alpha와 DirectWrite 합성은 구현하지 않았습니다. 게임 화면 자체를 흐리게 하거나 프로세스에 주입하지 않습니다. 창 모드/테두리 없는 창에서 먼저 검증해야 하며 호환성을 보장하지 않습니다.

자동 테스트는 설정 범위/저장/복구, 글자 alpha=1, Windows 실제 창의 배경 alpha·학습/플레이 style 전환·원문 선택을 검사합니다. 게임 화면상의 최종 픽셀·글자 가장자리 품질·실 입력 도달·성능을 측정한 테스트는 아닙니다.

공식 근거:
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setlayeredwindowattributes
- https://learn.microsoft.com/en-us/windows/win32/winmsg/window-features#layered-windows
