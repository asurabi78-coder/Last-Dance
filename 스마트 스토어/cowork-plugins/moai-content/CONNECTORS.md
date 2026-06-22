# moai-content 커넥터 가이드

## WordPress (Cowork 내장 커넥터)

WordPress 사이트에 블로그 포스트를 직접 발행합니다.

### 연결 방법

1. Claude Cowork > **Settings** > **Connectors**
2. **WordPress** 선택 > **Connect**
3. WordPress.com 계정 인증 (OAuth)
4. 발행할 사이트 선택

### 스킬 내 동작

스킬 실행 시 WordPress 커넥터 연결 여부를 자동 확인합니다:
- **연결됨**: 블로그 카피 생성 → WordPress에 직접 발행 (카테고리, 태그, 특성 이미지 자동 설정)
- **미연결**: "WordPress 커넥터가 연결되어 있지 않습니다. Settings > Connectors에서 WordPress를 연결하세요." 안내 후, 마크다운 카피만 생성합니다

### 활용 스킬

- `blog`: WordPress 블로그 포스트 생성 및 발행/예약

### 참고

- 네이버 블로그, 티스토리, 브런치, Ghost 등은 Cowork 커넥터가 없으므로 콘텐츠 생성까지만 지원합니다 (발행은 수동)
- WordPress.org (자체 호스팅)는 WordPress.com 계정 연동이 필요합니다 (Jetpack 플러그인)
