# -*- coding: utf-8 -*-
"""
스모크 테스트 — 본인 PC에서 실행해 각 API 키가 실제로 동작하는지 1건씩 확인.
사용법:  .venv\\Scripts\\activate  →  python test_apis.py
키 '값'은 출력하지 않고, 통과/실패만 표시합니다.
"""
from core import config, naver_keyword, copy_gpt, image_gen, sourcing


def line(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}")


def main():
    print("=== .env 키 감지 ===")
    for k in ["NAVER_AD_ACCESS_LICENSE", "NAVER_AD_SECRET_KEY", "NAVER_AD_CUSTOMER_ID",
              "OPENAI_API_KEY", "GEMINI_API_KEY", "REMOVE_BG_API_KEY", "DOMEGGOOK_API_KEY"]:
        print(f"  {'O' if config.present(k) else 'X'} {k}")

    print("\n=== ① 네이버 검색광고(키워드) ===")
    try:
        df = naver_keyword.related_keywords("반팔티")
        line("네이버 키워드", not df.empty, f"{len(df)}개 키워드")
    except Exception as e:
        line("네이버 키워드", False, str(e)[:120])

    print("\n=== ①-2 네이버 쇼핑 상품수 ===")
    try:
        from core import naver_keyword as nk
        if nk.shopping_available():
            cnt = nk.shopping_total("반팔티")
            line("네이버 쇼핑", cnt > 0, f"상품수={cnt:,}")
        else:
            line("네이버 쇼핑", False, "NAVER_CLIENT 키 없음")
    except Exception as e:
        line("네이버 쇼핑", False, str(e)[:120])

    print("\n=== ② 도매꾹 소싱 ===")
    try:
        rows, real = sourcing.search("반팔티")
        line("도매꾹", real, "실데이터" if real else "모의 폴백(스펙/키 확인 필요)")
    except Exception as e:
        line("도매꾹", False, str(e)[:120])

    print("\n=== ③ OpenAI(GPT) 카피 ===")
    try:
        d = copy_gpt.generate("테스트 반팔티", "반팔티", features="쿨드라이", provider="openai")
        line("OpenAI 카피", bool(d.get("title")), d.get("title", "")[:40])
    except Exception as e:
        line("OpenAI 카피", False, str(e)[:120])

    print("\n=== ④ 이미지(Gemini 우선, 실패시 OpenAI) ===")
    try:
        imgs, eng = image_gen.generate_image("a simple red apple on white background, product photo")
        line("이미지(Gemini→OpenAI)", len(imgs) > 0, f"{len(imgs)}장 / 엔진={eng}")
    except Exception as e:
        line("Gemini 이미지", False, str(e)[:120])

    print("\n완료. FAIL 항목은 해당 키/권한/모델명을 확인하세요.")


if __name__ == "__main__":
    main()
