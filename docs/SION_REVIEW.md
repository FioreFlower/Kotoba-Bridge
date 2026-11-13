# Sion 비교 준비 검토 (2026-11-13)

현재 설치 카탈로그/실행 어댑터에 포함하지 않으며 가중치 다운로드, pip 설치, remote code 실행을 하지 않았다.

## 확인한 자료와 한계
- 모델 카드: https://huggingface.co/alice-noa-chan/sion_translate-1.5-mrt
- 고정 런타임 의존성: https://github.com/gaon12/sion_translate/blob/ccccf5742909efffb8571a9cabfd9b70977e1ec4/pyproject.toml
- 검토한 로더: https://huggingface.co/alice-noa-chan/sion_translate-1.5-mrt/blob/main/portable/sion_portable.py (변동 가능한 main; 실행 전 고정 리비전 필요)

카드의 CPU 문장당 약 5초는 FP32·8스레드·beam 4 제작자 측정이며 INT8 속도가 아니다. 커스텀 encoder-decoder로 현재 llama.cpp/chat JSON 경로에 바로 연결할 수 없다. GGUF나 CTranslate2 변환 가능성을 검증하지 않았다.

카드의 portable FP32 safetensors는 약 1.09GB, INT8 state_dict는 약 0.41GB다. INT8은 torch 2.13.0+cpu/onednn의 한 환경 검증이며 FP32와 40문장 중 17문장만 동일 출력이었다. 이는 제작자의 진단이며 프로젝트의 독립 검증이나 일반적인 품질 점수가 아니다. TorchAO 형식의 기존 model_int8.pt와 portable INT8은 서로 다른 경로다.

읽은 로더는 safetensors 또는 weights_only=True로 읽고 strict=True로 상태를 적용한다. 그러나 로더 자체가 Python 코드이며 런타임을 monkey-patch하고, manifest/sidecar 검사만으로 전체 의존성의 신뢰성이 보장되지 않는다. 기존 일반 체크포인트로 fallback할 수 있는 래퍼는 그대로 실행하지 않을 계획이다. 허용 경로·고정 manifest 해시·고정 런타임·감사한 FP32 전용 로더부터 분리해야 한다.

pyproject는 Python >=3.11, torch >=2.8 및 Transformers/NumPy/SentencePiece 등 폭넓은 의존성을 요구하며 그대로 pip 설치하면 정확한 재현 환경이 아니다. 라이선스는 카드/런타임상 MIT이나 AI-Hub 데이터 고지는 전체 학습 데이터 권리 확인을 대신하지 않는다. 기본 재배포 채택은 보류한다.

## 비교 실험 설계 (아직 실행하지 않음)
1. 가중치 및 CPU 휠의 실제 총 다운로드 크기를 먼저 산정하고 별도 사용자 승인. 기존 Qwen 다운로드 승인을 재사용하지 않는다.
2. 런타임 고정 커밋·잠금 파일·휠 해시·라이선스와 모델 고정 리비전/해시를 검토한다. 비밀/게임 자료 없는 별도 환경에서 설치 후 네트워크를 차단한다. safetensors가 임의 Python 코드를 안전하게 만드는 것은 아니다.
3. 기존 docs/evaluation의 동일 합성 12문장을 source=ja/target=ko 원문 입력으로 사용한다. chat 지시문을 억지로 삽입하지 않는다. CPU 2스레드·FP32와 INT8을 각각 측정하고 beam/추론 설정을 기록한다. 제작자 조건 재현용 8스레드 결과는 별도 표로 분리한다.
4. 모델 로딩, 첫 문장, warm p50/p95, CPU 시간·peak RSS, 원문/출력·숫자/부정/인칭/말투 오류를 기록한다. 언어 혼합·거부·시간 초과도 실패로 보존한다. 동일 입력이어도 모델 내부 설정/토크나이저가 달라 완전히 동일 연산량은 아니다.
5. Qwen의 Go IPC+HTTP 포함 지연과 Sion 순수 추론 시간을 직접 순위화하지 않는다. 어댑터 연결 후 동일 경계로 추가 측정하며 OCR→표시 전체와 게임 FPS는 Windows 실기로 별도 검증한다.

현재 Sion 속도·번역 품질·Windows 동작은 미측정이다. 가벼움/무검열/성인 표현 충실도/저사양 지원을 보장하지 않는다.
