# 실제 게임 후킹 시험 준비와 현재 한계

## 확인한 엔진

공식 Textractor v5.2.0 English-only ZIP(35,242,917 bytes)의 SHA-256은 `3efdcf390261fcfb6a44220113c68b06eba22a3ef441ac618208238b52ee7974`이다. 다운로드 출처는 [공식 릴리스](https://github.com/Artikash/Textractor/releases/tag/v5.2.0)이며 릴리스 태그가 가리키는 소스 커밋은 `3e283975c8f0cf1bb8f1818e18e909196970c96b`이다. 코드 검토에 사용했던 최신 기본 브랜치 커밋과 릴리스 소스는 구분해야 한다. 재현 빌드로 소스와 배포 바이너리가 일치하는지는 검증하지 않았다. 공식 HTTPS 다운로드에서 측정한 해시는 독립 서명 체크섬이나 보안 감사가 아니다.

[Windows Server 2025 x64 감사 실행](https://github.com/FioreFlower/Kotoba-Bridge/actions/runs/43498180130), 코드 커밋 `ac30f009f293f8fd275980c7099dba5df07b33b2`:

| 파일 | x64 | x86 |
|---|---|---|
| TextractorCLI.exe | Authenticode Valid | Authenticode Valid |
| texthook.dll | Authenticode Valid | Authenticode Valid |
| MSVCP140.dll | Authenticode Valid | Authenticode Valid |
| VCRUNTIME140.dll | Authenticode Valid | Authenticode Valid |
| VCRUNTIME140_1.dll | Authenticode Valid | 해당 파일 없음 |

CLI 내 인증서에서 공개 개발자 주체 `Open Source Developer, Akash Mozumdar`, Certum 코드 서명 체인과 DigiCert 타임스탬프 인증서를 정적으로 확인했다. 실제 Windows 신뢰 판단은 위 CI의 Get-AuthenticodeSignature 결과다. 다른 PC/시각의 폐기 확인·정책은 달라질 수 있고 서명이 유효해도 취약점 부재나 SAC/백신 통과를 보장하지 않는다. **이 결과는 Textractor 파일에 대한 것이며 Kotoba 앱을 서명한 것이 아니다.** 신뢰 저장소·보안 설정을 변경하지 않았다.

PE 의존성 정적 검사에서 CLI는 Windows 시스템 DLL, Microsoft VC++ 런타임과 UCRT에 의존했다. x64 CLI는 VCRUNTIME140_1도 필요하다. x64 후킹 DLL은 KERNEL32/ADVAPI32, x86 후킹 DLL은 KERNEL32/USER32/GDI32/ADVAPI32를 가져온다. 모든 가능한 지연 로딩·동적 의존성을 조사한 것은 아니다. 누락/오류 시 공식 Microsoft 런타임 설치를 별도 검토하며 임의 DLL 사이트나 보안 경고 우회로 해결하지 않는다.

## 라이선스·정식 배포 판단

Textractor는 GPL v3다. 현재 MIT 클라이언트는 독립된 CLI의 텍스트 입출력을 사용하고 엔진 소스/DLL/EXE를 포함하지 않는다. 별도 프로세스라는 형식만으로 모든 GPL 결합 문제를 해소했다고 단정하지 않는다. 이 공식 ZIP에는 이름 기준 LICENSE/COPYING/NOTICE 파일을 찾지 못했으며 이를 허가 부재나 위반의 확정 판단으로 해석하지 않는다. 우리가 재배포한다면 라이선스 사본, 해당 버전의 완전한 대응 소스·변경·빌드 자료 제공 방식, MinHook 등 하위 구성요소와 Microsoft 런타임의 별도 조건을 검토해야 한다. 현재는 재포장/동봉하지 않는다.

공개 릴리스는 2022년, 확인한 기본 브랜치 마지막 커밋은 2023년이다. permissive 내부 IPC/클립보드 읽기/해제 ACK 부재도 남아 있어 **기본 권장 또는 정식 번들 엔진으로 승인하지 않았다.** 서명 유효성만으로 이 위험을 해결하지 않는다.

## 종료 시험 결과

위 Windows 합성 시험에서 서로 다른 두 일본어 대사를 실제 후킹 수신하고 연속 목업 처리했다. 종료 전 texthook.dll이 로드되어 있었고, 입력 중지 후:

- 소유 CLI가 종료됨.
- 자체 테스트 프로그램은 살아 있음.
- 최대 3초의 관찰 범위 안에서 테스트 프로그램의 모듈 목록에 texthook.dll이 없음.
- 별도 자체 테스트 프로그램을 종료한 경우 대상 종료를 감지하고 입력을 정리함.

모듈 부재 관찰은 해당 보호 없는 x64 fixture에만 해당한다. 모든 후크/메모리 변경이 복구되었다는 보증이나 실제 게임 결과가 아니다. upstream에 명시적인 해제 ACK가 없으므로 앱은 여전히 '제거 완료 확인 불가'라고 표시한다. 비동기 detach 전달을 위해 EOF 전에 짧은 유예를 추가했고, 소유 프로세스 종료에 실패하면 핸들을 유지하고 재연결을 막으며 종료 성공을 주장하지 않는다. UI의 전송 정지는 먼저 적용되지만 CLI 정리에는 수 초 걸릴 수 있다.

## 실제 PC 시험 전 단계

1. **대상 확인:** 사용자가 게임의 실행 파일/경로와 해당 실행 인스턴스를 직접 확인한다. 런처·브라우저·인증 프로세스를 게임으로 추정하지 않는다. 온라인/안티치트 게임에는 사용하지 않는다. 정상 인터넷 인증은 유지한다.
2. **데이터 보존:** 기존 세이브가 있다면 사용자가 확인한 공식 저장 위치에서 게임을 닫고 별도 복사본을 만든다. 저장 위치를 추측해 AppData/문서 전체를 수집하지 않는다. 기존 세이브가 없다면 없다고 기록하며 백업했다고 주장하지 않는다. 새 게임 진입/자동 저장의 발생 여부는 게임별로 다르므로 사용자 조작으로 진행한다.
3. **실행 전 승인:** 별도 Textractor 설치/실행과 정확한 게임 인스턴스 연결에 대해 범위를 설명하고 명시적으로 승인받는다. 공개 CI/합성 시험 승인을 사용자 PC/실제 게임 실행 승인으로 대체하지 않는다. 번역 제공자에 실제 전송하는 승인은 연결 동의와 별도다.
4. **첫 시험:** 정상 인증된 게임에서 이미 저장했거나 잃어도 되는 지점으로 사용자가 이동한다. API 전송을 끈 로컬 후보 미리보기부터 확인한다. 합성 fixture 성공을 근거로 실제 게임 호환성을 미리 확정하지 않는다.
5. **연속 번역 시험:** 정확한 후보를 비교해 선택하고, 제공자·비용/전송 범위를 확인한 후 짧은 대사 구간만 연속 시험한다. 중복/이름 혼입·지연·정지·게임 종료·OCR 복귀를 각각 확인한다. 키·대사·게임 이미지를 로그/공개 이슈에 남기지 않는다.
6. **중단 기준:** 보호·보안·권한 경고, 충돌, 원치 않은 후보, 대상 불일치, 종료 확인 실패가 나오면 즉시 전송을 정지한다. 관리자 승격/안티치트 우회/인증 차단/보안 기능 해제/임의 패치를 하지 않는다. 후크 제거가 불확실하면 게임을 저장할 수 있는 정상 상태인지 사용자가 판단하고 직접 종료한다.

현재 작업 환경은 Linux와 격리된 Windows CI이며 사용자 Windows PC를 직접 조작한 결과가 없다. 실제 게임 시험에 필요한 실행 파일 식별/승인/사용자 PC 조작 경로가 준비되기 전에는 연결을 진행하지 않는다. 실제 게임·32비트 연결·저사양/전체 지연·완전한 후크 복구는 미검증이다.

참고: [Microsoft Get-AuthenticodeSignature](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/get-authenticodesignature), [Textractor 릴리스 소스 라이선스](https://github.com/Artikash/Textractor/blob/3e283975c8f0cf1bb8f1818e18e909196970c96b/LICENSE).
