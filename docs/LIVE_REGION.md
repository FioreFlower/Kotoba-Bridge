# 게임 위 대사 영역 편집

`LiveRegionEditor`는 스크린샷을 만들지 않고 현재 데스크톱 위에 초록 테두리 4개와 모서리 손잡이 4개를 표시합니다. 내부를 덮는 창은 만들지 않습니다. 테두리를 드래그하면 이동하고, 모서리를 드래그하면 반대 모서리를 유지하면서 크기가 바뀝니다. 별도 설정 창에서 왼쪽 X·위쪽 Y·너비·높이를 물리 픽셀 단위로 입력해 적용할 수 있습니다. Enter는 수치 적용, 확정 버튼은 결과 전달, 취소·설정 창 닫기·편집 창에서 Esc는 취소입니다. 다른 게임 창에 포커스가 있으면 Esc가 이 앱에 전달된다고 보장하지 않습니다. 설정 창의 취소 버튼을 사용하세요.

편집 중에는 게임 위 손잡이 부분이 클릭을 받습니다. 편집 모드를 사용자가 명시적으로 열었을 때만 이 창을 표시합니다. 게임 중앙을 투명 창으로 덮거나 게임의 프로세스·렌더링·보안 설정을 변경하지 않습니다. 독점 전체화면에서 이 창이 보인다고 보장하지 않으며 창 모드/테두리 없는 창 모드에서 사용합니다.

## 부모 앱 통합 계약

```python
from live_region import LiveRegionEditor, ensure_physical_dpi, validate_region
editor = LiveRegionEditor(root, initial_region, monitors, on_select, on_cancel)
```

- `monitors`는 `mss.monitors[1:]`에서 얻은 **실제 모니터들의 물리 좌표 사전**입니다. 가상 데스크톱 전체 바운딩 박스인 `monitors[0]`을 넣지 않습니다.
- 부모는 생성 전에 캡처·번역 파이프라인을 중지하고 진행 중 응답을 무효화해야 합니다. 모듈은 캡처·OCR·네트워크·설정 저장·자동 재개 함수를 호출하지 않습니다. 모듈만으로 부모 스레드의 캡처를 정지시킬 수 없습니다.
- `initial_region`은 크기 제한과 모니터 포함 여부를 먼저 검증합니다. 유효하지 않으면 `ReaderError`가 발생하고 UI를 만들지 않습니다. 임의로 다른 화면의 영역으로 바꾸지 않습니다.
- `on_select(Region)`는 확정 시 한 번 호출합니다. 편집 창을 모두 닫은 후 호출합니다. 부모는 이 콜백에서 **새로 읽은 실제 모니터 목록으로 재검증**해야 합니다(편집 도중 모니터 분리/해상도 변경 가능). 그 다음 임시 결과 반영·로컬 미리보기·명시적 재시작 흐름을 수행합니다.
- `on_cancel()`는 취소 시 한 번 호출합니다. 기존 `Region`은 frozen dataclass이고 편집 값은 별도 초안이라 초기 설정이 변하지 않습니다. 생성 도중 예외가 나면 부분 생성 UI를 정리하고 예외를 부모에 전달합니다; 이 경우 생성자가 취소 콜백을 대신 호출하지 않습니다.
- 부모는 편집기를 하나만 열고, 종료 시 `editor.cancel()`로 정리할 수 있습니다. 해당 모듈은 앱의 API 키·동의·비용·번역·학습 설정을 바꾸지 않습니다.

## 좌표와 DPI

좌표는 가상 데스크톱 기준 물리 픽셀입니다. 왼쪽/위쪽에 있는 보조 모니터의 음수 좌표를 유지합니다. DPI 비율을 임의로 곱하거나 Tk의 논리 좌표를 캡처 좌표로 사용하지 않습니다. 드래그는 `GetPhysicalCursorPos`의 시작점 대비 차이를 사용하고, 테두리는 DPI-aware UI 스레드에서 `SetWindowPos`로 배치합니다. `ensure_physical_dpi()`는 **현재 스레드가 per-monitor aware인지 확인**하고 아니면 실패합니다. 전역 DPI 설정을 중간에 바꾸지 않습니다. 부모는 Tk 생성 전 startup DPI 설정을 해야 하며 시작 시 설정 API의 호출 성공을 추정해서는 안 됩니다.

한 영역 전체가 한 실제 모니터에 들어와야 합니다. 모니터 사이 빈 공간·화면 바깥·여러 모니터에 걸친 영역은 거부합니다. 드래그 중 유효하지 않은 후보는 마지막 유효한 초안을 유지합니다. 시작점 기준 이동이므로 다른 모니터 안으로 완전히 들어오면 그 위치로 옮길 수 있고, 수치 입력으로도 옮길 수 있습니다. 크기는 기존 캡처 제한인 20×20 이상 3840×2160 이하를 따릅니다. 모서리가 반대쪽을 넘으면 뒤집는 대신 최소 크기에서 멈춥니다.

Microsoft [GetWindowRect 문서](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowrect)는 반환값의 DPI 가상화와 보이지 않는 resize border 포함 가능성을 설명합니다. 같은 문서는 `DWMWA_EXTENDED_FRAME_BOUNDS`의 DWM 경계는 DPI 조정되지 않는다고 구분합니다. **이 편집 모듈은 게임 창의 GetWindowRect나 DWM 경계를 사용하지 않으므로 둘을 혼합하지 않습니다.** 부모의 창 추적 코드에서 GetWindowRect를 쓸 때도 같은 per-monitor context와 캡처 좌표계를 확인해야 합니다. 보이지 않는 프레임·DPI 차이가 기존 문제의 원인이었다는 진단은 아직 검증하지 않았습니다.

공식 근거: [GetPhysicalCursorPos](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getphysicalcursorpos), [SetWindowPos](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowpos), [GetAwarenessFromDpiAwarenessContext](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getawarenessfromdpiawarenesscontext).

## 검증 범위

Linux에서 pure geometry/초안 트랜잭션 단위 테스트와 Python 문법 검사를 수행했습니다. 실제 Windows 테두리 배치·핸들 조작·다중 DPI·Tk top-level HWND 동작·게임 호환성은 미검증입니다. Windows 10 22H2/11에서 100/125/150/200% 배율, 음수 좌표 모니터, 화면 가장자리, 모니터 분리, 취소 후 기존 영역 유지, 편집 동안 캡처 중지, 설정 창 종료 후 모든 테두리 제거를 실기 확인해야 합니다. 이 구현만으로 물리 좌표 문제가 해결됐다고 단정하지 않습니다.
