# 스마트스토어 통합 웹앱 — 실행법 (Phase 2: 실제 API 연동)

> 흐름: **① 키워드 → ② 소싱 → ③ 상세페이지 → ④ 이미지**
> 실데이터: 네이버 검색광고 / 도매꾹 / OpenAI(GPT) / Gemini + remove.bg
> 외부 통신이 막힌 환경에서는 각 단계가 자동으로 **모의(폴백)** 로 동작합니다.

## 1. 준비물
- Windows + Python 3.10+
- 상위 폴더(`Last Dance`)의 `.env` (키 들어있음)

## 2. 설치 (최초 1회) — cmd
```bat
cd "C:\Users\user\Desktop\Last Dance\통합앱_prototype"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 3. ⭐ 먼저 키 점검 (스모크 테스트)
```bat
.venv\Scripts\activate
python test_apis.py
```
- 각 API가 실제로 되는지 1건씩 PASS/FAIL로 보여줍니다(키 값은 출력 안 함).
- 여기서 통과하는 기능부터 실데이터로 쓰면 됩니다.

## 4. 실행
```bat
streamlit run app.py
```
→ 브라우저 `http://localhost:8501`. 사이드바에서 **실데이터 사용** 토글 / LLM(GPT 기본) 선택.

## 5. 검증 완료된 것 / PC에서 확인할 것
- ✅ (이 환경에서 검증) 문법, 모듈 import, 앱 부팅(healthz 200), 실패 시 모의 폴백
- ⛳ (PC에서 확인 필요) 실제 API 호출 — **개발 환경에선 외부 통신이 차단**돼 라이브 테스트를 못 했습니다. `test_apis.py`로 본인 PC에서 확인하세요.

## 6. 모듈별 메모
| 기능 | 파일 | 상태 |
|------|------|------|
| 키워드 | `core/naver_keyword.py` | 기존 작동 앱의 HMAC 서명 로직 그대로 사용 → 신뢰도 높음 |
| 카피 | `core/copy_gpt.py` | OpenAI Chat Completions(REST). 모델 `OPENAI_MODEL`(기본 gpt-4o-mini) |
| 이미지 | `core/image_gen.py` | Gemini `generateContent` + remove.bg. 모델 `GEMINI_IMAGE_MODEL`(기본 gemini-2.5-flash-image) |
| 소싱 | `core/sourcing.py` | 도매꾹 오픈API **엔드포인트/파라미터 최종 확인 필요**. 확정 전 모의 폴백 |

## 7. 비용·주의
- 이미지(Gemini)·카피(GPT)는 **호출당 과금**(본인 키). 먼저 1건씩 테스트로 단가 확인 권장.
- AI 이미지는 연출/배경/인포그래픽 용도, **제품 본컷은 실사** 권장(과장광고 방지).
- `.env`는 외부 공유·깃 커밋 금지(`.gitignore`에 `.env` 추가).
- `OPENAI_MODEL` / `GEMINI_IMAGE_MODEL` / `DOMEGGOOK_API_BASE` 는 `.env`에서 조정 가능.

## 8. 다음 단계(원하면)
- 도매꾹 API 스펙 확정 → 실데이터 연결
- 네이버 쇼핑 API로 상품수/경쟁 보강, 상품화 점수식 고도화
- (보너스) 네이버 커머스 API로 업로드 패키지 생성
