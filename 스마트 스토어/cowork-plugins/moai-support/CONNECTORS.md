# moai-support 커넥터 가이드

## Slack (Cowork 내장 커넥터)

고객 지원 채널 메시지 조회, 에스컬레이션 알림 전송에 사용합니다.

### 연결 방법

Claude Cowork에서 Slack 커넥터를 연결합니다:

1. Claude Cowork > **Settings** > **Connectors**
2. **Slack** 선택 > **Connect**
3. Slack 워크스페이스 인증 (OAuth)
4. 접근 허용할 채널 선택

### 스킬 내 동작

스킬 실행 시 Slack 커넥터 연결 여부를 자동 확인합니다:
- **연결됨**: Slack 채널에서 CS 문의를 직접 조회하고, 에스컬레이션 알림을 전송합니다
- **미연결**: "Slack 커넥터가 연결되어 있지 않습니다. Settings > Connectors에서 Slack을 연결하세요." 안내 후, 수동 입력으로 진행합니다

### 활용 스킬

- `ticket-triage`: Slack 채널에서 CS 문의 자동 수집 및 분류
- `escalation-manager`: 에스컬레이션 시 담당자에게 Slack DM 알림
- `draft-response`: Slack 스레드에 응답 초안 작성

---

## Notion (Cowork 내장 커넥터)

KB(Knowledge Base) 문서를 Notion 데이터베이스로 관리합니다.

### 연결 방법

1. Claude Cowork > **Settings** > **Connectors**
2. **Notion** 선택 > **Connect**
3. Notion 워크스페이스 인증
4. 접근 허용할 페이지/데이터베이스 선택

### 스킬 내 동작

스킬 실행 시 Notion 커넥터 연결 여부를 자동 확인합니다:
- **연결됨**: Notion 데이터베이스에 KB 문서를 직접 생성/업데이트합니다
- **미연결**: "Notion 커넥터가 연결되어 있지 않습니다. Settings > Connectors에서 Notion을 연결하세요." 안내 후, 마크다운 파일로 KB 문서를 생성합니다

### 활용 스킬

- `kb-article`: Notion 데이터베이스에 KB 문서 생성/업데이트
- `escalation-manager`: Notion에 에스컬레이션 로그 기록
