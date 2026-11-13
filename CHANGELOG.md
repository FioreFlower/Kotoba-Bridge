# 0.1.0 개발 경위와 최종 범위

1. 초기 Python/Tk + MSS + Tesseract + DeepL 시제품 구현, mock 번역/비용/취소 테스트.
2. 요청에 따라 학습/기록/복습 JSON과 사전 외부 링크, 플레이 클릭 통과 모드 추가.
3. Windows 7 이상 요구 검토: OS/런타임/네이티브 OCR/32비트의 미검증과 EOL 문제 기록.
4. 사용자가 Windows 10 이상으로 범위를 변경: Windows 10 22H2 x64/Windows 11 x64를 1차 대상으로 결정. Win7/8 요구 제거.
5. Go + 별도 UI 제안에 따라 Go 코어로 OCR 실행·번역·안정화·비용 상태를 이전하고 Tk UI는 유지. Go/C#/Python 비교 기록을 보존.

최종 구현은 Go+Python/Tk이며, C# 제품/완성 설치파일/검증된 저사양 제품으로 주장하지 않는다. Library ZIP은 소스·테스트·문서·Go 코어 교차 빌드·Windows 패키징 레시피를 포함한다. 실제 Windows, 일본어 OCR 품질, 유료 API, GUI 클릭 통과, installer, 성능은 별도 검증 필요.
