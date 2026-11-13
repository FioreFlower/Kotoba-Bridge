# 후킹 입력 연동 검토와 구현 경계

> 후속 구현 안내: 이 문서는 CLI 연동 이전의 조사 기록입니다. 현재 별도 Textractor 5.2.0 CLI의 명시적 연결·실제 후보 수신·선택 원문 1회 번역을 실험적으로 구현했습니다. 최신 상태와 미완성 기능은 [HOOK_CLI.md](HOOK_CLI.md)를 우선 확인하세요. 아래의 미구현 표기는 조사 당시 범위입니다.


검토일: 2026-11-13. 이 문서는 설계·정적 소스 조사 결과다. **실제 프로세스 연결, 주입, 후보 자동 탐색, 후크 해제는 구현·실기 검증 완료가 아니다.** 사용자 요구인 게임 선택 → 주입 전 동의 → 후보 자동 탐색 → 실시간 확인·추천·사용자 선택은 계속 개발 목표로 유지한다.

## 현재 코드에서 확인한 범위

`input_sources.py`의 `CandidateSession`은 세대 구분, 후보 32개·입력 2,000자·이벤트 1,000개 제한, 종료 시 버퍼 삭제, 명시적 선택을 제공한다. 추천은 문자열 길이·일본어 문자·문장부호·반복에 따른 휴리스틱이며 정확도를 보장하지 않는다. 이는 입력 상태 모델이고 프로세스 열거나 후킹하는 코드가 아니다.

`input_ui.py`는 사용자가 누르는 클립보드 1회 읽기와 편집 후 외부 전송 확인, 합성 후보 체험을 제공한다. 실제 후보를 가져오는 소켓·파일·도구 어댑터는 없다. 합성 예제의 이름·잡음·대사 후보는 게임에서 발견한 결과가 아니다. 기존 상세 배경은 [TEXT_INPUT_SOURCES.md](TEXT_INPUT_SOURCES.md)를 참고한다. 이 검토에서는 코드나 기존 문서를 변경하지 않았다.

## 공식 인터페이스 재확인

공식 GitHub API로 확인한 기본 브랜치 HEAD는 다음과 같다. 변경 가능한 브랜치 링크 대신 아래 고정 커밋의 소스를 기준으로 판단했다.

| 프로젝트 | 조사 커밋 | 확인된 경계 | 충족하지 못하는 부분 |
| --- | --- | --- | --- |
| Textractor | `df5b830d1757a66aa162f8081e99d42c9bd50488` | 호스트 콜백 및 선택 문장 클립보드 확장 | 별도 실행 중인 앱의 프로세스/후보 목록을 제어하는 안정된 외부 서비스 계약은 미확인 |
| LunaTranslator | `85c2234f34bab38def18e4f8f7c1e702e1344ade` | 공개 원문/번역 WebSocket, 클립보드 출력, 내부 DLL 콜백 | 공개 서비스 목록에 프로세스/후보 열거·선택·해제 API를 찾지 못함; 기본 서비스 바인딩 보안 검토 필요 |

### Textractor

[host/host.h](https://github.com/Artikash/Textractor/blob/df5b830d1757a66aa162f8081e99d42c9bd50488/host/host.h)의 `Host::Start`는 프로세스 연결/해제, 텍스트 스레드 생성/제거, 출력 콜백을 받는다. `FindHooks`, `GetThread`, `DetachProcess`도 있다. [GUI/mainwindow.cpp](https://github.com/Artikash/Textractor/blob/df5b830d1757a66aa162f8081e99d42c9bd50488/GUI/mainwindow.cpp)는 프로세스 목록과 콜백을 UI에 연결한다. 즉 필요한 내부 기능은 있지만 이 C++ 함수들을 그대로 외부 IPC API로 부를 수 있는 것은 아니다.

[copyclipboard.cpp](https://github.com/Artikash/Textractor/blob/df5b830d1757a66aa162f8081e99d42c9bd50488/extensions/copyclipboard.cpp)의 `ProcessSentence`는 선택 상태와 게임 PID 여부를 검사한 뒤 문장만 `CF_UNICODETEXT`로 쓴다. PID, 후보 ID, 세션, 이벤트 순서와 종료 이벤트는 수신자에게 전달되지 않는다. 문장만으로 출처를 인증하거나 여러 후보를 복원할 수 없다. [extension.h](https://github.com/Artikash/Textractor/blob/df5b830d1757a66aa162f8081e99d42c9bd50488/extensions/extension.h)의 메타데이터 구조를 이용하는 새 확장은 별도 개발·라이선스 검토 대상이다.

### LunaTranslator

[공식 Network Service 문서](https://docs.lunatranslator.org/en/apiservice.html)는 `/api/ws/text/origin`과 `/api/ws/text/trans`를 명시한다. [servicecollection.py](https://github.com/HIllya51/LunaTranslator/blob/85c2234f34bab38def18e4f8f7c1e702e1344ade/src/LunaTranslator/network/server/servicecollection.py)의 `TextOutputOrigin`, `TextOutputTrans`, `registerall`과 [textoutput/websocket.py](https://github.com/HIllya51/LunaTranslator/blob/85c2234f34bab38def18e4f8f7c1e702e1344ade/src/LunaTranslator/textio/textoutput/websocket.py)의 `Outputer.dispatch`에서 실제 경로와 문자열 출력을 확인했다. 이것은 원문 스트림 수신의 실현 가능성을 보여 주지만 후보 목록 API는 아니다. 본 조사에서 공개 문서·등록 목록에 후보/프로세스 제어 경로를 찾지 못했다는 의미이며 모든 버전에 없다고 단정하지 않는다.

[textsource/texthook.py](https://github.com/HIllya51/LunaTranslator/blob/85c2234f34bab38def18e4f8f7c1e702e1344ade/src/LunaTranslator/textio/textsource/texthook.py)의 `initdll`은 `LunaHost32.dll`/`LunaHost64.dll`과 `Luna_Start`, `Luna_FindHooks`, `Luna_DetachProcess`, `Luna_QueryThreadHistory`를 연결한다. 후보의 PID·주소·컨텍스트를 갖는 `ThreadParam`과 생성/제거/출력 콜백도 있다. 이를 활용하려면 네이티브 ABI, 정확한 DLL 버전, 스레드·수명, GPL 결합과 배포 의무를 따로 검토해야 한다. 이 내부 DLL을 MIT 앱에 바로 로드하는 방식은 이번 계획의 기본 경로가 아니다.

## 새로 확인한 네트워크 보안 제약

고정 커밋 [tcpservice.py](https://github.com/HIllya51/LunaTranslator/blob/85c2234f34bab38def18e4f8f7c1e702e1344ade/src/LunaTranslator/network/server/tcpservice.py)의 `TCPService.init`은 IPv4 `0.0.0.0`에 바인딩한다. `handle_client`는 비활성화된 경로를 확인하고 요청을 핸들러에 전달하며, 검토한 경로에는 연결별 인증 토큰 검증이 보이지 않는다. 응답에는 광범위한 CORS 허용도 설정되어 있다. 실제 외부 접근 가능성은 실행 설정·방화벽에 달려 있으며 이번에는 포트를 열거나 접속해 시험하지 않았다.

따라서 Kotoba Bridge가 `127.0.0.1`에 접속한다는 사실만으로 upstream 서비스 전체가 로컬 전용이 되지는 않는다. localhost 프록시를 앞에 추가하는 것만으로 기존 `0.0.0.0` 리스너의 노출이 사라지는 것도 아니다. **현재 버전의 네트워크 서비스를 자동 켜거나 기본 권장 연동으로 배포하지 않는다.** 원문뿐 아니라 기록·번역 관련 서비스도 함께 노출될 수 있는 구성을 검토해야 한다. 방화벽 허용, 보안 제품 비활성화, 관리자 자동 승격, TLS 검증 해제를 해결책으로 안내하지 않는다. upstream의 로컬 전용·인증 지원 또는 독립적으로 검토한 수신 전용 출력 어댑터가 준비될 때 다시 평가한다.

## MIT와 GPL을 구분한 현실적인 경로

[Textractor LICENSE](https://github.com/Artikash/Textractor/blob/df5b830d1757a66aa162f8081e99d42c9bd50488/LICENSE)와 [LunaTranslator LICENSE](https://github.com/HIllya51/LunaTranslator/blob/85c2234f34bab38def18e4f8f7c1e702e1344ade/LICENSE)는 GPL version 3 본문이다. Kotoba Bridge 원본 코드의 MIT 표기가 이 소스를 재라이선스할 권한을 주지 않는다.

1. **현재 사용 가능한 최소 흐름:** 외부 도구에서 사용자가 게임·후킹 동의·후보를 직접 선택하고 Kotoba Bridge에서 문장을 수동으로 붙여넣어 확인한다. 외부 도구를 자동 실행·주입하지 않는다. 자동 후보 UX 요구를 완성하는 기능은 아니지만 현행 인터페이스로 가능한 범위다.
2. **다음 입력 연동 후보:** 별도로 설치한 도구가 이미 선택한 원문을 로컬 전용 출력 브리지로 전송한다. Kotoba Bridge는 독립적인 일반 텍스트 이벤트 계약을 받아 표시·번역한다. 소스 코드나 GPL DLL을 MIT 배포물에 넣지 않는다. 단순 클립보드 변환 브리지는 출처 정보가 없다는 한계를 그대로 갖는다.
3. **통합 후보 마법사 목표:** upstream 기여 또는 별도 GPL 호환 구성요소에서 엔진 내부 콜백을 공개 이벤트로 변환하는 어댑터가 필요하다. 어댑터의 소스·빌드·고지·라이선스와 Kotoba Bridge 수신기를 별도 산출물로 관리한다. 설치자가 GPL 구성요소를 함께 재배포하면 해당 배포 의무도 검토한다. 별도 프로세스라는 형식만으로 결합 관계의 법적 문제가 자동 해소된다고 주장하지 않는다.

현재는 새 GPL 어댑터 구현이나 배포를 수행하지 않았다. 일반 텍스트 수신, 전용 호스트 확장, DLL 직접 링크는 서로 다른 배포 조합이며 법적 확정 판단을 내리지 않는다. 게임 약관과 대사 저작권은 도구 라이선스와도 별개다.

## 필요한 브리지 계약 — 미구현 제안

우선 `selected_text`만 지원하는 수신기와 `candidates` 기능을 구분한다. 기능 협상이 안 되면 후보 탐색 버튼을 비활성화한다. 선택 문장 한 개를 가상의 여러 후보로 만들어 자동 탐색이라고 표시하지 않는다.

| 이벤트/기능 | 필수 의미 |
| --- | --- |
| `hello` | 프로토콜 주버전, 공급자/릴리스, 세션 nonce, 지원 기능; 모르는 주버전은 거절 |
| `source_bound` | 사용자가 선택·동의한 실행 인스턴스 식별자; PID만으로 식별하지 않고 생성 시각 등과 확인. 원문 전송 동의와 별개 |
| `candidate_added/updated/removed` | 불투명한 후보 ID와 원문, 해당 세션의 증가 순번; 이름/잡음도 후보로 표시하며 추측 확정 금지 |
| `selected_text` | 공급자에서 사용자가 선택한 텍스트임을 표시. 출처 증명 수준과 부족한 메타데이터를 명시 |
| `stopped/source_exited/error` | 입력 중단과 대상 종료. 해제 확인 없으면 후크 제거 완료라고 표시하지 않음 |
| `heartbeat` | 연결 생존만 확인. 게임 출처나 주입 해제의 증명으로 쓰지 않음 |

전송은 Windows 현재 사용자 전용 ACL과 원격 클라이언트 거부를 갖춘 named pipe를 우선 검토한다. 보안 속성은 구현·시험 전 보장하지 않는다. 연결마다 무작위 세션 식별자, peer 확인과 버전 협상을 적용한다. 같은 사용자 권한의 악성 프로그램으로부터 완전한 보호를 보장하지 않는다. 메시지는 길이 지정 UTF-8 JSON으로 최대 바이트 크기를 먼저 검사하고 깊이·필드·문자 수를 제한한다. 실행 명령·파일 경로·후킹코드·HTML 실행 기능을 수신 프로토콜에 포함하지 않는다.

수신기에는 현재의 32 후보·2,000자·1,000 이벤트 세션 제한에 더해 bounded queue, 초당 이벤트 제한과 UI 업데이트 합치기가 필요하다. 지속 입력은 무제한 세션으로 풀지 말고 중단 후 재동의 또는 명시적 정책을 설계한다. 외부 원문을 받았다고 즉시 API에 보내지 않는다. 로컬 미리보기, 명시적 후보 선택, 입력원별 외부 전송 동의를 거친 단일 스트림만 기존 번역 한도·중복 제거·늦은 응답 폐기에 연결한다.

프로세스 선택 목록 자체는 주입 없이 구현할 수 있지만 실제 외부 도구에 선택 대상이 바인딩되었음을 별도로 확인해야 한다. 외부 엔진이 주입하는 단계는 이번 연결에 대한 명시 동의 후에만 진행하며 무인 재주입을 허용하지 않는다. 자동 후보 탐색은 지원 엔진의 후보 콜백을 활용하되 전체 메모리의 무제한 탐색으로 대체하지 않는다. 이름·중복·부분 대사 때문에 추천은 참고만 제공하고 사용자가 게임의 실제 대사와 비교해 선택한다.

중지/게임 종료/연결 상실/권한 오류/포커스 이탈 시 입력과 자동 번역을 멈추고 세대를 바꾸며 후보·대기열·문맥을 지운다. 포커스를 잃어도 동작하는 외부 도구의 상태와 Kotoba Bridge 상태를 혼동하지 않는다. 늦은 응답은 버리되 이미 발생한 API 비용이 환불됐다고 표시하지 않는다. 프로필에는 도구 버전·게임의 로컬 식별자·선택 재식별 정보만 저장하고 대사·키를 넣지 않는다. 다른 게임으로 자동 재연결하지 않는다. OCR 복귀에는 영역 확인과 사용자 시작이 필요하다.

## 다음 단계와 완료 판단

1. 순수 합성 입력 생산자로 위 프로토콜 파서·세션 수명·기능 협상을 구현하고 후보 자동 갱신 UX를 시험한다. 시연 표시는 유지한다. 파서 시험 성공은 게임 후킹 성공이 아니다.
2. Windows에서 ACL·원격 거부·위장 세션·잘못된 버전·대형/잘린 JSON·폭주·PID 재사용·게임 종료·포커스 이탈·후보 변경 중 늦은 번역을 시험한다. API는 목업만 사용한다.
3. 별도 도구 출력 어댑터의 라이선스·배포·정확한 엔진 릴리스와 이벤트 정보 충족 여부를 확정한다. 출력 전용/후보 제어 지원을 명시하고 누락 기능을 비활성화한다. 연결·해제 확인 없이 성공 표시하지 않는다.
4. 허용된 Windows 오프라인 게임에서 명시 동의하에 실제 엔진 호환성, 종료/복구, 후보 정확성, CPU·메모리·지연을 측정한다. 보안 경고·권한 실패 시 중단하며 우회하지 않는다. 32비트 게임과 64비트 게임은 별도 검증한다.

이번 검토에서 완료한 것은 기존 입력 코드 읽기, 공식 문서·고정 소스·HEAD 재확인, GPL/네트워크 경계 및 프로토콜 설계다. 새 런타임 연동·주입·게임 시험·벤치마크·유료 호출은 수행하지 않았다. 통합 프로세스 선택과 실제 후보 자동 탐색은 사용자 목표로 남아 있으며, 위 엔진 어댑터와 Windows 검증이 필요하다.
