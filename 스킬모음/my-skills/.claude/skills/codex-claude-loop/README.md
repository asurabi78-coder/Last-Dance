# Codex-Claude Loop 스킬 사용법

## 기본 사용 시나리오

### 1️⃣ 새로운 기능 개발

```
👤 사용자: "로그인 기능을 OAuth 2.0으로 구현해줘"

🤖 Claude: 
[먼저 계획을 세움]
- OAuth 2.0 플로우 설계
- 보안 토큰 관리 방식
- 에러 핸들링 전략
...

[계획이 완성되면]
"이 계획을 Codex로 검증하겠습니다"
- 어떤 모델을 사용할까요? (gpt-5 / gpt-5-codex)
- Reasoning effort? (low / medium / high)

👤 사용자: "gpt-5-codex, high"

🤖 Claude:
[Codex에게 계획 검증 요청]
$ echo "Review this OAuth plan..." | codex exec -m gpt-5-codex --config model_reasoning_effort="high" --sandbox read-only

[Codex 피드백 요약]
"Codex가 2가지 이슈를 발견했습니다:
1. CSRF 토큰 검증 누락
2. Refresh token 로테이션 필요

계획을 수정할까요, 아니면 이대로 진행할까요?"
```

### 2️⃣ 코드 리뷰 & 개선

```
👤 사용자: "이 코드를 Codex-Claude loop으로 리뷰해줘"

🤖 Claude:
[먼저 코드 분석]
"몇 가지 개선점을 발견했습니다..."

[Codex로 교차 검증]
$ echo "Review this code for bugs and performance..." | codex exec --sandbox read-only

[양쪽 피드백 통합]
"Claude 발견: 가독성 이슈 3개
 Codex 발견: 잠재적 메모리 누수 1개, 성능 최적화 2개

수정을 진행할까요?"

👤 사용자: "응"

🤖 Claude:
$ echo "Fix the identified issues..." | codex exec --sandbox workspace-write --full-auto
```

### 3️⃣ 버그 수정 (AI가 실수했을 때)

```
👤 사용자: "Codex가 만든 코드에 버그가 있어"

🤖 Claude:
"어떤 버그인지 확인했습니다. Codex가 실수했으므로 
제가 수정하고 다시 Codex에게 검증받겠습니다"

[Claude가 수정]
[Codex로 재검증]
$ echo "Verify this fix..." | codex exec resume --last

"수정 완료! Codex가 확인했습니다. 
다음 작업은 Codex와 계속할까요? (마지막 정리자 규칙)"
```

## 주요 명령어 패턴

### 계획 검증
```bash
echo "Review this plan: [계획내용]" | codex exec -m gpt-5-codex --config model_reasoning_effort="high" --sandbox read-only
```

### 실행 (편집 필요)
```bash
echo "Implement: [구현내용]" | codex exec -m gpt-5-codex --sandbox workspace-write --full-auto
```

### 이어서 작업
```bash
echo "Continue with next step" | codex exec resume --last
```

### 긴급 수정
```bash
echo "Fix this bug: [버그설명]" | codex exec resume --last
```

## 언제 이 스킬을 쓰나?

✅ **이럴 때 사용:**
- 복잡한 기능 개발 (여러 단계 필요)
- 높은 품질이 중요한 코드
- 보안/성능이 critical한 작업
- 리팩토링 대규모 작업

❌ **이럴 땐 과함:**
- 간단한 일회성 수정
- 프로토타입/실험 코드
- 개인 학습용 간단한 예제

## 실전 팁

### 💡 Tip 1: 모델 선택
- **gpt-5**: 빠른 일반 작업
- **gpt-5-codex**: 복잡한 코드 분석

### 💡 Tip 2: Reasoning Effort
- **low**: 간단한 검증
- **medium**: 일반적인 작업 (권장)
- **high**: critical한 로직, 보안 관련

### 💡 Tip 3: 교차 리뷰 타이밍
```
작은 변경 → 간단히 확인
중간 변경 → 상대 AI가 리뷰
큰 변경 → 완전한 교차 검증
```

### 💡 Tip 4: 컨텍스트 유지
```
Codex가 마지막 수정 → Codex resume로 계속
Claude가 마지막 수정 → Claude가 다음 계획
```

## 실제 워크플로우 예시

```
1. 👤 "결제 시스템 만들어줘"
   
2. 🤖 Claude가 계획 수립
   - Stripe API 통합
   - 웹훅 처리
   - 환불 로직
   
3. 🤖 Codex로 계획 검증
   $ codex exec ... --sandbox read-only
   
4. 📝 피드백: "웹훅 서명 검증 추가 필요"
   
5. 🤖 Claude가 계획 수정
   
6. ✅ 재검증 통과
   
7. 🔨 Codex가 구현
   $ codex exec ... --sandbox workspace-write --full-auto
   
8. 👀 Claude가 코드 리뷰
   "변수명 개선 제안 3개"
   
9. 🔧 Codex가 정리
   $ codex exec resume --last
   
10. ✅ 완료! (다음은 Codex부터 시작)
```

핵심은 **"계획 → 검증 → 실행 → 리뷰 → 핸드오프"** 루프입니다! 🔄