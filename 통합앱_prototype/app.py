# -*- coding: utf-8 -*-
"""
스마트스토어 통합 웹앱 — Phase 2 (실제 API 연동 + 실패 시 모의 폴백)
흐름: 키워드 분석 → 소싱 → 상세페이지 → 이미지
실데이터: 네이버 검색광고 / 도매꾹 / OpenAI(GPT) / Gemini + remove.bg
※ 외부 통신이 막힌 환경에서는 각 단계가 자동으로 '모의'로 폴백합니다.
"""
import os
import random

import pandas as pd
import streamlit as st

from concurrent.futures import ThreadPoolExecutor
from core import config, naver_keyword, sourcing, copy_gpt, image_gen, detail_template, datalab_rank, store, batch, commerce, edit_util, usage, cro, naver_seo, video_gen
import streamlit.components.v1 as components

st.set_page_config(page_title="스마트스토어 통합 웹앱", page_icon="🛒", layout="wide")


def _check_password():
    """APP_PASSWORD 환경변수가 있으면 로그인 요구. 미설정이면 게이트 비활성(로컬용)."""
    pw = config.get("APP_PASSWORD", "")
    if not pw:
        return True
    if st.session_state.get("_authed"):
        return True
    st.title("🔒 로그인")
    st.caption("이 앱은 비공개입니다. 비밀번호를 입력하세요.")
    _pw_in = st.text_input("비밀번호", type="password", key="_login_pw")
    if st.button("로그인", key="_login_btn"):
        if _pw_in == pw:
            st.session_state["_authed"] = True
            _rr = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
            if _rr:
                _rr()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
    return False


if not _check_password():
    st.stop()

KEYS = ["NAVER_AD_ACCESS_LICENSE", "NAVER_AD_SECRET_KEY", "NAVER_AD_CUSTOMER_ID",
        "NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY", "REMOVE_BG_API_KEY", "DOMEGGOOK_API_KEY",
        "NAVER_COMMERCE_CLIENT_ID", "NAVER_COMMERCE_CLIENT_SECRET", "FAL_KEY"]

CATEGORIES = ["(선택 안 함)", "패션의류", "패션잡화", "화장품/미용", "디지털/가전",
              "가구/인테리어", "출산/육아", "식품", "스포츠/레저", "생활/건강",
              "여가/생활편의", "반려동물", "문구/오피스", "자동차용품"]


def ss(k, v):
    if k not in st.session_state:
        st.session_state[k] = v


ss("kw_selected", [])
ss("sourcing_pick", None)
ss("copy_result", None)
ss("editing_saved_id", None)
ss("edit_nonce", 0)


def _safe_rerun():
    fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if fn:
        fn()


def _item_text(it):
    """카피 항목이 dict로 와도 안전하게 문자열로 변환(크래시 방지)."""
    if isinstance(it, dict):
        for _k in ("title", "name", "text", "headline", "label", "prompt", "content", "value"):
            _v = it.get(_k)
            if _v:
                return str(_v)
        for _v in it.values():
            if isinstance(_v, str) and _v.strip():
                return _v
        return ""
    return "" if it is None else str(it)


def _items_lines(items):
    """items 리스트 → 문자열 리스트(빈 값 제거). dict 항목 안전 처리."""
    return [t for t in (_item_text(i) for i in (items or [])) if t]


def _add_detail_image(b64):
    """생성 이미지(b64)를 상세페이지 추가목록에 넣음(중복 제거·최근 12장 유지)."""
    uri = "data:image/png;base64," + b64
    lst = st.session_state.setdefault("detail_images", [])
    if uri not in lst:
        lst.append(uri)
        if len(lst) > 12:
            st.session_state["detail_images"] = lst[-12:]


def mock_keywords(seed):
    base = (seed or "키워드").strip()
    random.seed(base)
    rows = []
    for v in [base, base + " 추천", base + " 남자", base + " 여성", base + " 세트",
              base + " 가성비", "기능성 " + base, base + " 정품"]:
        vol = random.randint(800, 60000)
        comp = random.choice(["낮음", "중간", "높음"])
        cs = {"낮음": 0.2, "중간": 0.5, "높음": 0.85}[comp]
        cnt = random.randint(500, 800000)
        score = round(100 * (vol/60000) * (1-cs)**0.5, 1)
        grade = "A" if score >= 70 else ("B" if score >= 45 else "C")
        rows.append({"키워드": v, "월검색량": vol, "경쟁도": comp,
                     "상품수": cnt, "경쟁률": round(cnt/vol, 2),
                     "상품화점수": score, "등급": grade})
    return pd.DataFrame(rows).sort_values("상품화점수", ascending=False).reset_index(drop=True)


# ----- 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    present = [k for k in KEYS if config.present(k)]
    st.caption(f".env 키 감지: {len(present)}/{len(KEYS)} (값 비공개)")
    with st.expander("키 상태"):
        for k in KEYS:
            st.write(("✅ " if config.present(k) else "⬜ ") + k)
    provider = "openai" if st.radio("상세페이지 LLM", ["GPT (OpenAI)", "Claude (Anthropic)"],
                                    index=0) == "GPT (OpenAI)" else "anthropic"
    use_real = st.toggle("실데이터 사용(API 호출)", value=True,
                         help="끄면 모든 단계가 모의 데이터로 동작합니다.")
    st.caption("외부 통신이 막힌 환경이면 자동으로 모의 폴백됩니다.")
    with st.expander("💰 사용량 / 추정 비용", expanded=False):
        _ut = usage.totals()
        st.metric("누적 추정 비용(USD)", f"${_ut['total']['cost']:.4f}")
        st.caption(f"호출 {_ut['total']['calls']}회 · 토큰 {_ut['total']['tokens']:,} · 이미지 {_ut['total']['images']}장")
        for _pv, _b in _ut["by_provider"].items():
            st.caption(f"· {_pv}: ${_b['cost']:.4f} (토큰 {_b['tokens']:,}, 이미지 {_b['images']})")
        _uper = st.radio("기간", ["일별", "주간", "월별"], horizontal=True, key="usage_period")
        _umap = {"일별": "day", "주간": "week", "월별": "month"}
        _uagg = usage.aggregate(_umap[_uper])
        if _uagg:
            _udf = pd.DataFrame(_uagg).set_index("period")
            st.bar_chart(_udf["cost"])
            st.caption("막대 = 기간별 추정 비용(USD)")
        else:
            st.caption("아직 사용 기록이 없습니다. (API 호출 시 자동 누적)")
        if st.button("기록 초기화", key="usage_reset"):
            usage.reset()
            _safe_rerun()
        st.caption("※ 추정치입니다(요금표 기반). 계정 잔액은 각 사 결제 페이지에서 확인하세요.")

st.title("🛒 스마트스토어 통합 웹앱")
st.caption("키워드 → 소싱 → 상세페이지 → 이미지")
t1, t2, t3, t4, t5 = st.tabs(["① 키워드", "② 소싱", "③ 상세페이지", "④ 이미지", "📦 배치 & 저장함"])

# ----- ① 키워드
with t1:
    st.subheader("① 키워드 자동 분석")
    cc, ck = st.columns([1, 2])
    category = cc.selectbox("카테고리(선택)", CATEGORIES, index=0)
    seed = ck.text_input("카테고리/키워드", placeholder="예: 로카티")
    if st.button("키워드 분석", type="primary"):
        hint = (seed or "").strip() or ("" if category == "(선택 안 함)" else category)
        if use_real and naver_keyword.available():
            try:
                df = naver_keyword.related_keywords(hint)
                df = naver_keyword.enrich_with_shopping(df)   # 상품수·경쟁률·등급 보강
                st.session_state["kw_df"] = df
                st.session_state["kw_src"] = "네이버 검색광고+쇼핑 API"
            except Exception as e:
                st.warning(f"실데이터 실패 → 모의로 대체: {e}")
                st.session_state["kw_df"] = mock_keywords(hint)
                st.session_state["kw_src"] = "모의(폴백)"
        else:
            st.session_state["kw_df"] = mock_keywords(hint)
            st.session_state["kw_src"] = "모의"
    if "kw_df" in st.session_state:
        st.caption("출처: " + st.session_state.get("kw_src", ""))
        df = st.session_state["kw_df"]
        if not df.empty:
            edf = df.copy()
            edf.insert(0, "선택", False)
            edited = st.data_editor(
                edf, use_container_width=True, hide_index=True, key="kw_editor",
                column_config={"선택": st.column_config.CheckboxColumn("선택", default=False)},
                disabled=[c for c in edf.columns if c != "선택"])
            checked = edited[edited["선택"]]["키워드"].astype(str).tolist()
            st.caption("체크: " + (", ".join(checked) if checked else "없음"))
            if st.button("✅ 선택 키워드 → ② 소싱", key="kw_to_src", type="primary"):
                if checked:
                    st.session_state["kw_selected"] = checked
                    st.session_state["sourcing_seed"] = checked[0]
                    st.success(f"{', '.join(checked)} → ② 소싱으로 전달됨 (② 탭으로 이동)")
                else:
                    st.warning("표에서 키워드를 체크하세요.")
        else:
            st.dataframe(df, use_container_width=True)

    with st.expander("🔥 분야별 인기검색어 TOP (데이터랩)", expanded=False):
        dcat = st.selectbox("분야 선택", datalab_rank.categories(), key="dl_cat")
        if st.button("인기검색어 가져오기", key="dl_btn"):
            if use_real:
                drows, dsrc = datalab_rank.get_top(dcat, count=20)
            else:
                drows, dsrc = [], "실데이터 OFF"
            st.session_state["dl_rows"] = drows
            st.session_state["dl_src"] = dsrc
        if "dl_rows" in st.session_state:
            st.caption("출처: " + st.session_state.get("dl_src", ""))
            drows = st.session_state["dl_rows"]
            if drows:
                ddf = pd.DataFrame(drows)
                ddf.insert(0, "선택", False)
                dedit = st.data_editor(
                    ddf, use_container_width=True, hide_index=True, key="dl_editor",
                    column_config={"선택": st.column_config.CheckboxColumn("선택", default=False)},
                    disabled=[c for c in ddf.columns if c != "선택"])
                dchecked = dedit[dedit["선택"]]["키워드"].astype(str).tolist()
                if st.button("✅ 선택 키워드 → ② 소싱", key="dl_use", type="primary"):
                    if dchecked:
                        st.session_state["kw_selected"] = dchecked
                        st.session_state["sourcing_seed"] = dchecked[0]
                        st.success(f"{', '.join(dchecked)} → ② 소싱으로 전달됨")
                    else:
                        st.warning("표에서 키워드를 체크하세요.")
        st.caption("비공식 데이터랩 소스라 네이버 변경 시 안 될 수 있음(개인용).")

    with st.expander("🏷️ 상품명 3안 · 해시태그 생성", expanded=False):
        nkw = st.text_input("키워드/상품", value=(st.session_state.get("kw_selected") or [""])[0], key="nm_kw")
        nfeat = st.text_input("특징(쉼표)", key="nm_feat")
        nbrand = st.text_input("브랜드(선택)", key="nm_brand")
        if st.button("상품명 생성", key="nm_btn"):
            if use_real and (copy_gpt.available_openai() or copy_gpt.available_anthropic()):
                try:
                    st.session_state["name_res"] = copy_gpt.product_names(
                        nkw or "상품", features=nfeat, brand=nbrand, provider=provider)
                except Exception as e:
                    st.error(f"상품명 생성 실패: {e}")
            else:
                st.info("실데이터 OFF 또는 LLM 키 없음")
        nd = st.session_state.get("name_res")
        if nd:
            for it in nd.get("names", []):
                v = it.get("검증", {})
                flag = "✅" if v.get("통과") else "⚠️"
                st.markdown(f"{flag} **[{it.get('유형','')}]** {it.get('상품명','')}")
                warn = []
                if v.get("권장초과(50)"):
                    warn.append(f"50자 초과({v.get('길이')}자)")
                if v.get("금지어"):
                    warn.append("금지어: " + ", ".join(v["금지어"]))
                st.caption(("⚠️ " + " · ".join(warn)) if warn else f"{v.get('길이')}자 · 통과")
            if nd.get("hashtags"):
                st.markdown("**해시태그:** " + " ".join("#" + str(h) for h in nd["hashtags"]))
            if nd.get("blog_titles"):
                st.markdown("**블로그 제목:** " + " / ".join(nd["blog_titles"]))

# ----- ② 소싱
with t2:
    st.subheader("② 공급처 소싱")
    sel = st.session_state.get("kw_selected", [])
    if True:
        if sel:
            st.caption("①에서 선택된 키워드: " + ", ".join(map(str, sel)))
        _seed = st.session_state.get("sourcing_seed") or (sel[0] if sel else "")
        kw = st.text_input("소싱 키워드 (직접 입력 가능)", value=_seed,
                           placeholder="예: 귀걸이 보관함")
        if st.button("소싱 후보 검색", type="primary"):
            if use_real:
                rows, real = sourcing.search(kw)
            else:
                rows, real = sourcing._mock(kw), False
            st.session_state["src_df"] = pd.DataFrame(rows)
            st.session_state["src_real"] = real
        _url_in = st.text_input("🔗 도매꾹 상품 링크로 소싱 (선택)",
                                placeholder="도매꾹 상품 페이지 URL 붙여넣기", key="src_url")
        if st.button("링크로 소싱 추가", key="src_url_btn"):
            if not _url_in.strip():
                st.warning("도매꾹 상품 링크를 입력하세요.")
            elif not use_real:
                st.info("실데이터 OFF — 링크 소싱은 실데이터 모드(API)에서 동작합니다.")
            else:
                _urows, _ureal = sourcing.search_by_url(_url_in)
                if _urows:
                    _new = pd.DataFrame(_urows)
                    if "src_df" in st.session_state and not st.session_state["src_df"].empty:
                        st.session_state["src_df"] = pd.concat([st.session_state["src_df"], _new], ignore_index=True).drop_duplicates(subset=["링크"], keep="last").reset_index(drop=True)
                    else:
                        st.session_state["src_df"] = _new
                    st.session_state["src_real"] = _ureal or st.session_state.get("src_real", False)
                    st.success("링크 상품을 소싱 목록에 추가했습니다.")
                else:
                    st.warning("링크에서 상품번호를 못 찾았거나 조회 실패. (도매꾹 상품 URL인지 확인)")
        if "src_df" in st.session_state:
            st.caption("출처: " + ("도매꾹 API" if st.session_state.get("src_real") else "모의(폴백)"))
            sdf = st.session_state["src_df"]
            if "최소주문수량" in sdf.columns:
                if st.checkbox("최소주문 1개만 보기", key="moq1_only",
                               help="도매꾹 unitQty(판매단위)=1 인 상품만 표시 (수량 미상은 제외)"):
                    sdf = sdf[sdf["최소주문수량"] == 1].reset_index(drop=True)
            if not sdf.empty:
                view = st.radio("보기", ["카드", "표"], horizontal=True, key="src_view")
                if view == "표":
                    st.dataframe(sdf, use_container_width=True, column_config={
                        "썸네일": st.column_config.ImageColumn("이미지"),
                        "링크": st.column_config.LinkColumn("링크", display_text="상품보기"),
                        "최소주문수량": st.column_config.NumberColumn("최소주문"),
                    })
                    pick = st.selectbox("상세페이지로 넘길 후보", sdf["상품후보"].tolist())
                    if st.button("이 후보 선택", key="pick_tbl"):
                        _trow = sdf[sdf["상품후보"] == pick]
                        _tthumb = str(_trow.iloc[0].get("썸네일") or "") if not _trow.empty else ""
                        st.session_state["sourcing_pick"] = {"keyword": kw, "product": pick, "thumb": _tthumb}
                        st.success(f"선택: {pick} → ③ 상세페이지" + (" (대표이미지 가져온)" if _tthumb else ""))
                else:
                    def _badge(sc):
                        return "🟢 A" if sc >= 70 else ("🟡 B" if sc >= 45 else "⚪ C")
                    rows = sdf.head(12).reset_index(drop=True)
                    ncol = 3
                    for r0 in range(0, len(rows), ncol):
                        cols = st.columns(ncol)
                        for j in range(ncol):
                            if r0 + j >= len(rows):
                                break
                            row = rows.iloc[r0 + j]
                            with cols[j]:
                                thumb = str(row.get("썸네일") or "")
                                if thumb:
                                    st.image(thumb, use_container_width=True)
                                else:
                                    st.markdown("<div style='height:130px;background:#f0f0f0;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#aaa'>이미지 없음</div>", unsafe_allow_html=True)
                                title = str(row["상품후보"])
                                link = str(row.get("링크") or "")
                                sc = float(row.get("점수") or 0)
                                if link:
                                    st.markdown(f"**[{title[:38]}]({link})**")
                                else:
                                    st.markdown(f"**{title[:38]}**")
                                st.caption(f"{_badge(sc)} · 점수 {sc} · 마진 +{int(row['예상마진']):,}원")
                                st.caption(f"사입 {int(row['사입원가']):,} → 판매 {int(row['예상판매가']):,}")
                                _moq = int(row.get("최소주문수량") or 0)
                                if _moq:
                                    st.caption("✅ 최소주문 1개" if _moq == 1 else f"⚠️ 최소주문 {_moq}개")
                                if st.button("이 상품으로 →", key=f"pick_{r0+j}"):
                                    st.session_state["sourcing_pick"] = {"keyword": kw, "product": title, "thumb": str(row.get("썸네일") or "")}
                                    st.success("선택됨 → ③ 상세페이지" + (" (대표이미지 가져온)" if str(row.get("썸네일") or "") else ""))

# ----- ③ 상세페이지
with t3:
    st.subheader("③ 상세페이지 카피")
    sp = st.session_state.get("sourcing_pick")
    dkw = sp["keyword"] if sp else (st.session_state.get("kw_selected") or [""])[0]
    dpr = sp["product"] if sp else ""
    c1, c2 = st.columns(2)
    kw_in = c1.text_input("키워드", value=dkw)
    _pr_pending = st.session_state.pop("pr_pending", None)
    pr_in = c2.text_input("상품명", value=(_pr_pending if _pr_pending is not None else dpr),
                          placeholder="예: DMPS 로카티 쿨드라이 반팔티")
    feat = st.text_input("핵심 특징(쉼표)", placeholder="쿨드라이, 남녀공용, ROKA 디테일")
    o1, o2, o3 = st.columns(3)
    mode_13 = o1.checkbox("13섹션 감정여정", value=True, help="Hero→Pain→…→CTA 13섹션 고전환 구조")
    do_human = o2.checkbox("문체 정리(humanize)", value=True, help="번역투·AI관용구 제거(호출 1회 추가)")
    include_img = o3.checkbox("AI 대표이미지(B)", value=True, help="상단 대표이미지 생성(과금)")
    _framework = st.selectbox("카피 방식(프레임워크)", ["PAS", "AIDA", "BAB"],
                              help="PAS=문제·자극·해결 / AIDA=주목·흥미·욕구·행동 / BAB=비포·애프터·브릿지")
    _sp_thumb = (sp or {}).get("thumb") if sp else ""
    if _sp_thumb:
        tc1, tc2 = st.columns([1, 4])
        try:
            tc1.image(_sp_thumb, width=110)
        except Exception:
            tc1.caption("(미리보기 불가)")
        use_thumb_img = tc2.checkbox("도매꾹 대표이미지 기반으로 AI 작업(권장)", value=True,
                                     help="새로 그리지 않고, 선택한 실제 상품 사진을 유지한 채 흰배경 메인컷으로 가공합니다.")
        tc2.caption("② 소싱에서 선택한 상품의 대표이미지를 가져왔습니다. (실패 시 텍스트 생성으로 자동 폴백)")
    else:
        use_thumb_img = False
        st.caption("ℹ️ ② 소싱에서 상품을 선택하면 대표이미지를 가져와 AI가 그 사진으로 작업합니다. (지금은 텍스트 생성)")
    with st.expander("🏷️ 상품명 3안·해시태그 (선택)"):
        if st.button("상품명 3안 생성", key="t3_name_btn"):
            if use_real and (copy_gpt.available_openai() or copy_gpt.available_anthropic()):
                try:
                    st.session_state["t3_name_res"] = copy_gpt.product_names(
                        kw_in or pr_in or "상품", features=feat, provider=provider)
                except Exception as _e:
                    st.error(f"상품명 생성 실패: {_e}")
            else:
                st.info("실데이터 OFF 또는 LLM 키 없음")
        _nr = st.session_state.get("t3_name_res")
        if _nr:
            _names = [it.get("상품명", "") for it in _nr.get("names", []) if it.get("상품명")]
            if _names:
                _pick_name = st.radio("상품명 3안", _names, key="t3_name_pick")
                if st.button("이 상품명 사용", key="t3_use_name"):
                    st.session_state["pr_pending"] = _pick_name
                    _safe_rerun()
            if _nr.get("hashtags"):
                st.caption("해시태그: " + " ".join("#" + str(h) for h in _nr["hashtags"]))
                if st.button("해시태그를 상세페이지 태그에 반영", key="t3_merge_tags"):
                    _cur = st.session_state.get("copy_result")
                    if _cur:
                        st.session_state["copy_result"] = edit_util.merge_hashtags(_cur, _nr["hashtags"])
                        st.success("태그에 반영됨. 아래 미리보기가 갱신됩니다.")
                        _safe_rerun()
                    else:
                        st.info("먼저 상세페이지를 생성하면 태그에 반영할 수 있습니다.")
        st.markdown("---")
        st.markdown("**🔍 상품명 SEO 점검 (네이버)**")
        _seo_targets = []
        if pr_in.strip():
            _seo_targets.append(("현재 상품명", pr_in.strip()))
        if _nr:
            for _it in _nr.get("names", []):
                if _it.get("상품명"):
                    _seo_targets.append((_it.get("유형", "안"), _it["상품명"]))
        if not _seo_targets:
            st.caption("상품명을 입력하거나 3안을 생성하면 SEO 점검이 표시됩니다.")
        for _slbl, _snm in _seo_targets:
            _ss = naver_seo.check_name_seo(_snm, kw_in)
            st.markdown(f"**[{_slbl}] {_ss['score']}/100 ({_ss['grade']})** · {_snm}")
            for _sc in _ss["checks"]:
                if _sc["level"] != "ok":
                    _sic = {"warn": "⚠️", "fail": "❌"}.get(_sc["level"], "•")
                    st.caption(f"{_sic} {_sc['name']}: {_sc['msg']}")
        st.caption("※ 네이버 공개 가이드 기반 휴리스틱 점검입니다.")
    if st.button("상세페이지 생성", type="primary"):
        ok = (provider == "openai" and copy_gpt.available_openai()) or \
             (provider == "anthropic" and copy_gpt.available_anthropic())

        def _make_hero():
            """대표이미지 작업(별도 스레드). (hero_dataurl, engine, warn) 반환. st.* 호출 금지."""
            if not (include_img and use_real and
                    (image_gen.available_gemini() or image_gen.available_openai())):
                return "", "", None
            imgs, eng, warn = None, None, None
            if use_thumb_img and _sp_thumb:
                try:
                    ref = image_gen.fetch_image_bytes(_sp_thumb)
                    imgs, _e = image_gen.edit_image(ref, image_gen.SCENE_PROMPTS["흰배경 메인컷"])
                    eng = "도매꾹기반·" + _e
                except Exception as e:
                    warn = f"도매꾹 이미지 기반 작업 실패 → 대체 생성 시도: {e}"
                    imgs, eng = None, None
            if not imgs:
                try:
                    ip = f"Studio e-commerce hero shot of {pr_in or kw_in}, clean white background, photorealistic, 1:1"
                    imgs, eng = image_gen.generate_image(ip)
                except Exception as e:
                    warn = (warn + " / " if warn else "") + f"대표이미지 생성 실패: {e}"
                    imgs = None
            if imgs:
                return "data:image/png;base64," + imgs[0], eng, None
            return "", "", warn

        with st.spinner("상세페이지 생성 중… (카피와 대표이미지를 동시에 처리합니다)"):
            with ThreadPoolExecutor(max_workers=1) as _ex:
                _hero_fut = _ex.submit(_make_hero)   # 이미지 백그라운드 시작(카피와 동시 진행)
                cr = None
                if use_real and ok:
                    try:
                        if mode_13:
                            cr = copy_gpt.generate_13(pr_in or "상품", kw_in or "키워드", features=feat, provider=provider, framework=_framework)
                        else:
                            cr = copy_gpt.generate(pr_in or "상품", kw_in or "키워드", features=feat, provider=provider)
                        if do_human:
                            cr = copy_gpt.humanize(cr, provider=provider)
                    except Exception as e:
                        st.error(f"카피 생성 실패: {e}")
                else:
                    cr = {"provider": "모의", "title": f"{kw_in} {pr_in} 가성비 추천",
                          "bullets": ["핵심 기능 요약", "흡한속건·가벼움", "남녀공용", "합리적 가격"],
                          "body": "(모의 문구) 실데이터 사용을 켜고 키를 넣으면 GPT가 생성합니다.",
                          "tags": [kw_in, pr_in, "가성비", "기능성"], "image_brief": ["메인컷", "디테일컷"]}
                hero_url, hero_eng, hero_warn = _hero_fut.result()

        if hero_warn:
            st.warning(hero_warn)
        if cr is not None:
            cr["hero"] = hero_url or ""
            if hero_url:
                cr["hero_engine"] = hero_eng
            st.session_state["copy_result"] = cr
            st.session_state["editing_saved_id"] = None
            st.session_state["edit_nonce"] = st.session_state.get("edit_nonce", 0) + 1
    cr = st.session_state.get("copy_result")
    if cr:
        tag = cr.get("provider", "")
        if cr.get("humanized"):
            tag += " · 문체정리✓"
        if cr.get("hero"):
            tag += f" · 이미지 {cr.get('hero_engine','')}"
        st.caption("생성: " + tag)
        # ✏️ 제목 직접 편집 — 커서로 글자 수정, Enter로 원하는 위치에서 줄바꿈
        _nonce = st.session_state.get("edit_nonce", 0)
        _title_edit = st.text_area(
            "✏️ 제목 직접 편집 (커서로 수정 · Enter로 원하는 위치에서 줄바꿈)",
            value=cr.get("title", ""), key=f"title_edit_{_nonce}", height=90,
            help="여기서 글자를 직접 고치고, 줄을 바꾸고 싶은 자리에서 Enter를 치면 미리보기 제목이 딱 그 위치에서 줄바꿈됩니다.")
        if _title_edit != cr.get("title", ""):
            cr["title"] = _title_edit
            st.session_state["copy_result"] = cr
        # 🎨 디자인 조정 — ＋/－ 버튼으로 한 칸씩 미세조절
        _DEF = detail_template.DESIGN_DEFAULTS
        with st.expander("🎨 디자인 조정 (크기·여백·색상 — ＋/－로 한 칸씩 미세조절)"):
            _dc1, _dc2, _dc3 = st.columns(3)
            _title_size = _dc1.number_input("제목 크기", 16, 80, _DEF["title_size"], 1, key="d_title_size")
            _sub_size = _dc2.number_input("부제목 크기", 10, 32, _DEF["sub_size"], 1, key="d_sub_size")
            _sec_size = _dc3.number_input("섹션제목 크기", 14, 48, _DEF["sec_size"], 1, key="d_sec_size")
            _dd1, _dd2, _dd3 = st.columns(3)
            _body_size = _dd1.number_input("본문 크기", 10, 28, _DEF["body_size"], 1, key="d_body_size")
            _line_h = _dd2.number_input("제목 줄간격", 0.8, 2.5, _DEF["line_height"], 0.05, format="%.2f", key="d_lh")
            _letter_s = _dd3.number_input("자간(em)", -0.10, 0.20, _DEF["letter_spacing"], 0.005, format="%.3f", key="d_ls")
            _de1, _de2, _de3 = st.columns(3)
            _title_gap = _de1.number_input("제목 아래 여백", 0, 80, _DEF["title_gap"], 1, key="d_gap")
            _word_keep = _de2.checkbox("단어 안 끊기(keep-all)", value=_DEF["word_keep"], key="d_keep",
                                       help="켜면 단어 중간에서 줄바꿈되지 않습니다. (Enter로 직접 넣은 줄바꿈은 항상 유지)")
            _align = _de3.radio("정렬", ["center", "left"], index=0, horizontal=True, key="d_align")
            _df1, _df2, _df3 = st.columns(3)
            _hero_bg = _df1.color_picker("배경색", _DEF["hero_bg"], key="d_bg")
            _hero_fg = _df2.color_picker("글자색", _DEF["hero_fg"], key="d_fg")
            _accent = _df3.color_picker("강조색(골드)", _DEF["accent"], key="d_accent")
            if st.button("기본값으로 초기화", key="d_reset"):
                for _k in ("d_title_size", "d_sub_size", "d_sec_size", "d_body_size", "d_lh",
                           "d_ls", "d_gap", "d_keep", "d_align", "d_bg", "d_fg", "d_accent"):
                    st.session_state.pop(_k, None)
                st.session_state.pop("design_opts", None)
                _safe_rerun()
        _design = {"title_size": int(_title_size), "sub_size": int(_sub_size), "sec_size": int(_sec_size),
                   "body_size": int(_body_size), "line_height": float(_line_h), "letter_spacing": float(_letter_s),
                   "title_gap": int(_title_gap), "word_keep": _word_keep, "align": _align,
                   "hero_bg": _hero_bg, "hero_fg": _hero_fg, "accent": _accent}
        st.session_state["design_opts"] = _design
        _sess_vid = st.session_state.get("product_video_url", "")
        # 새 영상이 생기면 체크박스/URL칸에 1회 자동 반영(키 위젯 stale 방지)
        if _sess_vid and not st.session_state.get("_vid_seeded"):
            st.session_state["embed_video"] = True
            st.session_state["vid_url_input"] = _sess_vid
            st.session_state["_vid_seeded"] = True
        _embed_vid = st.checkbox("🎬 상세페이지에 영상 삽입", key="embed_video",
                                 help="④에서 만든 영상이 자동 입력됩니다. mp4 URL을 직접 붙여넣어도 됩니다. (스마트스토어 상세 HTML은 영상이 제거되니 '동영상 등록란'에 별도 업로드)")
        _vid_for_page = ""
        if _embed_vid:
            _vid_for_page = st.text_input("영상 URL", key="vid_url_input",
                                          placeholder="④에서 영상 생성 시 자동 입력 · 또는 mp4 URL 붙여넣기").strip()
        _detail_imgs = st.session_state.get("detail_images") or []
        if _detail_imgs:
            _di1, _di2 = st.columns([3, 1])
            _di1.caption("🖼️ ④에서 추가한 이미지 " + str(len(_detail_imgs)) + "장이 상세페이지에 들어갑니다.")
            if _di2.button("이미지 비우기", key="clear_detail_imgs"):
                st.session_state["detail_images"] = []
                _safe_rerun()
        try:
            sec_imgs = st.session_state.get("section_images") or {}
            if sec_imgs:
                st.caption(f"④에서 만든 구간 이미지 {len(sec_imgs)}장 자동 배치됨")
            if cr.get("sections"):
                page = detail_template.build_detail_html_13(cr, hero_img=cr.get("hero", ""),
                                                            meta={"상품명": pr_in or cr.get("title", "")},
                                                            section_images=sec_imgs, design=_design,
                                                            video_url=_vid_for_page, extra_images=_detail_imgs)
            else:
                page = detail_template.build_detail_html(cr, hero_img=cr.get("hero", ""),
                                                         meta={"상품명": pr_in or cr.get("title", "")},
                                                         design=_design, video_url=_vid_for_page,
                                                         section_images=sec_imgs, extra_images=_detail_imgs)
            components.html(page, height=1000, scrolling=True)
            st.download_button("상세페이지 HTML 다운로드", page.encode("utf-8"), "상세페이지.html", "text/html")
            if cr.get("sections"):
                _edit_page = detail_template.build_detail_html_13(cr, hero_img=cr.get("hero", ""),
                                                                  meta={"상품명": pr_in or cr.get("title", "")},
                                                                  section_images=sec_imgs, design=_design,
                                                                  video_url=_vid_for_page, extra_images=_detail_imgs,
                                                                  editable=True)
            else:
                _edit_page = detail_template.build_detail_html(cr, hero_img=cr.get("hero", ""),
                                                               meta={"상품명": pr_in or cr.get("title", "")},
                                                               design=_design, video_url=_vid_for_page,
                                                               section_images=sec_imgs, extra_images=_detail_imgs,
                                                               editable=True)
            st.download_button("✏️ 직접 편집용 HTML 다운로드 (글자 클릭해 수정)", _edit_page.encode("utf-8"),
                               "상세페이지_편집용.html", "text/html", key="edit_dl",
                               help="받은 파일을 브라우저로 열고 → 아무 글자나 클릭해 띄어쓰기·줄바꿈·내용 수정 → 우측 하단 💾 저장")
            st.caption("✏️ '직접 편집용' 파일은 브라우저로 열어 글자를 클릭해 수정하고, 우측 아래 '📷 이미지로 저장'으로 PNG를 받아 스마트스토어에 이미지로 업로드하세요(가장 확실).")
            _ss_html = detail_template.build_smartstore_html(cr, meta={"상품명": pr_in or cr.get("title", "")},
                                                             section_images=sec_imgs, extra_images=_detail_imgs)
            st.download_button("🟢 스마트스토어용 HTML 다운로드 (인라인·표/스크립트 제거)", _ss_html.encode("utf-8"),
                               "스마트스토어_상세.html", "text/html", key="ss_dl",
                               help="스마트에디터 ONE의 'HTML' 모드 붙여넣기용. style/script/table/a 제거·인라인 스타일. (이미지는 스토어 정책상 막힐 수 있어 이미지 저장 방식 권장)")
            _editing_id = st.session_state.get("editing_saved_id")
            if _editing_id:
                st.caption(f"저장함 항목 편집 중: {_editing_id}")
                _sc1, _sc2 = st.columns(2)
                if _sc1.button("💾 덮어쓰기 저장", key="save_overwrite"):
                    try:
                        store.update_detail(_editing_id, cr, html=page,
                                            meta={"상품명": pr_in or cr.get("title", ""), "키워드": kw_in})
                        st.success(f"덮어쓰기 저장됨: {_editing_id}")
                    except Exception as _e:
                        st.error(f"저장 실패: {_e}")
                if _sc2.button("💾 새 항목으로 저장", key="save_asnew"):
                    try:
                        _sid = store.save_detail(cr, html=page,
                                                 meta={"상품명": pr_in or cr.get("title", ""), "키워드": kw_in},
                                                 hero=cr.get("hero"))
                        st.session_state["editing_saved_id"] = None
                        st.success(f"새로 저장됨: {_sid}")
                    except Exception as _e:
                        st.error(f"저장 실패: {_e}")
            else:
                if st.button("💾 이 상세페이지 저장", key="save_detail_btn"):
                    try:
                        _sid = store.save_detail(cr, html=page,
                                                 meta={"상품명": pr_in or cr.get("title", ""), "키워드": kw_in},
                                                 hero=cr.get("hero"))
                        st.success(f"저장됨: {_sid}  ·  '📦 배치 & 저장함' 탭에서 확인하세요.")
                    except Exception as _e:
                        st.error(f"저장 실패: {_e}")
        except Exception as e:
            st.error(f"상세페이지 렌더 실패: {e}")
        with st.expander("텍스트(카피)만 보기"):
            st.markdown(f"**제목:** {cr.get('title','')}")
            if cr.get("sections"):
                for sec in cr["sections"]:
                    if sec.get("headline") or sec.get("items"):
                        st.markdown(f"**[{sec.get('label','')}]** {sec.get('headline','')}")
                        if sec.get("sub"):
                            st.caption(sec["sub"])
                        for it in _items_lines(sec.get("items")):
                            st.markdown(f"- {it}")
            else:
                st.markdown("**셀링포인트:**\n" + "\n".join(f"- {b}" for b in cr.get("bullets", [])))
                st.markdown(f"**상세:** {cr.get('body','')}")
            st.markdown("**태그:** " + " ".join("#" + t for t in _items_lines(cr.get("tags"))))
        with st.expander("✏️ 카피 수정"):
            _nz = st.session_state.get("edit_nonce", 0)
            _ed_title = st.text_input("제목", value=cr.get("title", ""), key=f"ed_title_{_nz}")
            _ed_tags = st.text_input("태그(쉼표)", value=", ".join(_items_lines(cr.get("tags"))), key=f"ed_tags_{_nz}")
            _sec_edits = {}
            for _sec in (cr.get("sections") or []):
                _k = _sec.get("key")
                st.markdown(f"**[{_sec.get('label','')}]**")
                _h = st.text_input("헤드라인", value=_sec.get("headline", ""), key=f"ed_h_{_nz}_{_k}")
                _sub = st.text_input("서브", value=_sec.get("sub", ""), key=f"ed_s_{_nz}_{_k}")
                _items = st.text_area("항목(줄바꿈)", value="\n".join(_items_lines(_sec.get("items"))),
                                      key=f"ed_i_{_nz}_{_k}", height=68)
                _sec_edits[_k] = {"headline": _h, "sub": _sub, "items_text": _items}
            if st.button("수정 적용", key=f"ed_apply_{_nz}"):
                _newcr = edit_util.apply_edits(cr, title=_ed_title, tags_text=_ed_tags,
                                               section_edits=_sec_edits or None)
                st.session_state["copy_result"] = _newcr
                st.success("수정 적용됨. 위 미리보기가 갱신됩니다.")
                _safe_rerun()
        with st.expander("🎯 전환율(CRO) 점검"):
            if st.button("점검 실행", key="cro_run"):
                st.session_state["cro_result"] = cro.audit(cr)
            _ar = st.session_state.get("cro_result")
            if _ar:
                st.metric("전환율 점수", f"{_ar['score']}/100  ·  등급 {_ar['grade']}")
                for _c in _ar["checks"]:
                    _ic = {"ok": "✅", "warn": "⚠️", "fail": "❌"}.get(_c["level"], "•")
                    st.markdown(f"{_ic} **{_c['name']}** — {_c['msg']}")
                if _ar["suggestions"]:
                    st.markdown("**개선 우선순위:**")
                    for _s in _ar["suggestions"]:
                        st.markdown(f"- {_s}")
            st.caption("※ 일반 전환율(CRO) 기준입니다. 네이버 검색노출(SEO)과는 별개입니다.")
        with st.expander("🆎 헤드라인 A/B 변형"):
            if st.button("헤드라인 2안 생성", key="ab_run"):
                if use_real and (copy_gpt.available_openai() or copy_gpt.available_anthropic()):
                    try:
                        st.session_state["ab_result"] = copy_gpt.headline_ab(
                            pr_in or cr.get("title", "상품"), kw_in or "키워드", features=feat, provider=provider)
                    except Exception as _e:
                        st.error(f"헤드라인 생성 실패: {_e}")
                else:
                    st.info("실데이터 OFF 또는 LLM 키 없음")
            _ab = st.session_state.get("ab_result")
            if _ab:
                _vcols = st.columns(2)
                for _vi, _v in enumerate(_ab["variants"]):
                    with _vcols[_vi % 2]:
                        st.markdown(f"**[{_v['label'] or ('안' + str(_vi + 1))}]**")
                        st.markdown(f"### {_v['headline']}")
                        if _v["sub"]:
                            st.caption(_v["sub"])
                        if st.button("이 헤드라인 적용", key=f"ab_apply_{_vi}"):
                            st.session_state["copy_result"] = edit_util.apply_headline(cr, _v["headline"], _v["sub"])
                            st.success("헤드라인을 카피에 반영했습니다. 위 미리보기가 갱신됩니다.")
                            _safe_rerun()
            st.caption("※ A/B 비교용 2안입니다. LLM 1회 호출(소량 과금).")

# ----- ④ 이미지
with t4:
    st.subheader("④ 이미지 생성")
    with st.expander("📷 내 상품 사진 → 흰배경 합성", expanded=False):
        up = st.file_uploader("상품 사진 업로드", type=["jpg", "jpeg", "png", "webp"], key="wb_up")
        if up is not None:
            st.image(up, caption="원본", width=240)
            if st.button("흰배경으로 합성", key="wb_btn"):
                if use_real and image_gen.available_removebg():
                    try:
                        out = image_gen.to_white_bg(up.getvalue())
                        st.image(out, caption="흰배경 합성 결과", width=240)
                        st.download_button("결과 PNG 저장", out, "white_bg.png", "image/png", key="wb_dl")
                    except Exception as e:
                        st.error(f"합성 실패: {e}")
                else:
                    st.info("REMOVE_BG_API_KEY 없음 또는 실데이터 OFF → 합성 불가")
    with st.expander("📸 사진으로 구간 이미지 확장(여러 컷)", expanded=False):
        ups = st.file_uploader("상품 사진 1~2장 업로드", type=["jpg", "jpeg", "png", "webp"],
                               accept_multiple_files=True, key="exp_up")
        use_thumb = st.checkbox("도매꾹 선택상품 썸네일 사용", value=False, key="exp_thumb",
                                help="②소싱에서 선택한 상품 썸네일을 기준 이미지로 사용")
        scenes = st.multiselect("만들 구간 이미지", list(image_gen.SCENE_PROMPTS.keys()),
                                default=list(image_gen.SCENE_PROMPTS.keys()), key="exp_scenes")
        _exp_dir = st.text_input("🎬 연출 지시(선택)", placeholder="예: 얼굴 자연스럽게 / 제품 클로즈업 / 밝고 화사하게", key="exp_dir")
        _exp_person = st.radio("인물", ["자동", "제품만(인물 없음)", "인물 포함(얼굴까지)"], horizontal=True, key="exp_person")
        if st.button("구간 이미지 생성", key="exp_btn"):
            ref = None
            if ups:
                ref = ups[0].getvalue()
            elif use_thumb:
                sp2 = st.session_state.get("sourcing_pick")
                turl = ""
                if "src_df" in st.session_state and sp2:
                    m = st.session_state["src_df"]
                    m = m[m["상품후보"] == sp2.get("product")]
                    if not m.empty:
                        turl = str(m.iloc[0].get("썸네일") or "")
                if turl:
                    try:
                        import requests as _rq
                        ref = _rq.get(turl, timeout=15).content
                    except Exception as e:
                        st.error(f"썸네일 불러오기 실패: {e}")
            if not ref:
                st.warning("사진을 업로드하거나, ②에서 상품 선택 후 '도매꾹 썸네일 사용'을 켜세요.")
            elif not (use_real and (image_gen.available_gemini() or image_gen.available_openai())):
                st.info("실데이터 OFF 또는 이미지 키 없음 → 생성 불가")
            elif not scenes:
                st.warning("만들 구간 이미지를 1개 이상 선택하세요.")
            else:
                st.image(ref, caption="기준 사진", width=200)
                _exp_d = (image_gen.PERSON_CLAUSES.get(_exp_person, "") + " " + _exp_dir).strip()
                results = image_gen.expand_from_reference(ref, scenes, direction=_exp_d)
                gcols = st.columns(2)
                for i, (scene, b64, eng, err) in enumerate(results):
                    with gcols[i % 2]:
                        if b64:
                            data = image_gen.b64_to_bytes(b64)
                            st.image(data, caption=f"{scene} · {eng}")
                            st.download_button("저장", data, f"{scene}.png", "image/png", key=f"exp_dl_{i}")
                        else:
                            st.error(f"{scene} 실패: {err}")
                _smap = {"흰배경 메인컷": "solution", "사용 연출컷": "story",
                         "배경 교체": "benefits", "디테일 클로즈업": "how"}
                simgs = {}
                for scene, b64, eng, err in results:
                    if b64 and scene in _smap:
                        simgs[_smap[scene]] = "data:image/png;base64," + b64
                if simgs:
                    st.session_state["section_images"] = simgs
                    st.success(f"{len(simgs)}장을 ③ 상세페이지 섹션에 배치 준비 완료 (③에서 자동 사용)")
        st.caption("주의: 제품 디테일(로고·글자)은 변형될 수 있어, 정품 디테일컷은 실사 권장.")
    with st.expander("🎨 배경 다양화(상품 사진 → 여러 배경)", expanded=False):
        _bgups = st.file_uploader("상품 사진 업로드", type=["jpg", "jpeg", "png", "webp"], key="bg_up")
        _bg_use_thumb = st.checkbox("도매꾹 선택상품 썸네일 사용", value=False, key="bg_thumb")
        _bg_sel = st.multiselect("배경 선택(여러 개)", list(image_gen.BACKGROUND_PRESETS.keys()),
                                 default=["순백 스튜디오", "파스텔 핑크", "우드 책상"], key="bg_sel")
        _bg_dir = st.text_input("🎬 연출 지시(선택)", placeholder="예: 인물 포함 / 그림자 강하게 / 미니멀하게", key="bg_dir")
        _bg_person = st.radio("인물", ["자동", "제품만(인물 없음)", "인물 포함(얼굴까지)"], horizontal=True, key="bg_person")
        _bg_add = st.checkbox("✅ 생성 결과를 상세페이지에 추가", value=True, key="bg_add_detail")
        if st.button("배경 버전 생성", key="bg_btn"):
            _bgref = None
            if _bgups is not None:
                _bgref = _bgups.getvalue()
            elif _bg_use_thumb:
                _sp3 = st.session_state.get("sourcing_pick")
                _turl = ""
                if "src_df" in st.session_state and _sp3:
                    _m = st.session_state["src_df"]
                    _m = _m[_m["상품후보"] == _sp3.get("product")]
                    if not _m.empty:
                        _turl = str(_m.iloc[0].get("썸네일") or "")
                if _turl:
                    try:
                        _bgref = image_gen.fetch_image_bytes(_turl)
                    except Exception as _e:
                        st.error(f"썸네일 불러오기 실패: {_e}")
            if not _bgref:
                st.warning("사진을 업로드하거나, ②에서 상품 선택 후 '도매꾹 썸네일 사용'을 켜세요.")
            elif not (use_real and (image_gen.available_gemini() or image_gen.available_openai())):
                st.info("실데이터 OFF 또는 이미지 키 없음 → 생성 불가")
            elif not _bg_sel:
                st.warning("배경을 1개 이상 선택하세요.")
            else:
                st.image(_bgref, caption="기준 사진", width=200)
                with st.spinner(f"{len(_bg_sel)}개 배경 생성 중…"):
                    _bg_d = (image_gen.PERSON_CLAUSES.get(_bg_person, "") + " " + _bg_dir).strip()
                    _bgres = image_gen.expand_backgrounds(_bgref, _bg_sel, direction=_bg_d)
                _bgcols = st.columns(2)
                for _bi, (_pname, _b64, _eng, _err) in enumerate(_bgres):
                    with _bgcols[_bi % 2]:
                        if _b64:
                            _bdata = image_gen.b64_to_bytes(_b64)
                            st.image(_bdata, caption=f"{_pname} · {_eng}")
                            st.download_button("저장", _bdata, f"bg_{_pname}.png", "image/png", key=f"bg_dl_{_bi}")
                            if _bg_add:
                                _add_detail_image(_b64)
                        else:
                            st.error(f"{_pname} 실패: {_err}")
        st.caption("※ 상품은 유지하고 배경만 교체합니다. 로고·글자가 있는 상품은 결과 확인 권장.")
    with st.expander("👗 AI 모델 착용컷 (상품 → 사람이 착용한 전신)", expanded=False):
        st.caption("상품 사진을 '사람이 착용한 컷'으로 만듭니다. ⚠️ 생성 특성상 상품 디테일(로고·패턴)이 다소 바뀔 수 있어요.")
        _meng = st.radio("엔진", ["Gemini (저렴)", "GPT (gpt-image-1)"], horizontal=True, key="mdl_eng")
        _mprov = "gemini" if _meng.startswith("Gemini") else "openai"
        _msrc = st.radio("기준 이미지", ["사진 업로드", "도매꾹 썸네일", "③ 대표이미지"], horizontal=True, key="mdl_src")
        _mup = None
        if _msrc == "사진 업로드":
            _mup = st.file_uploader("상품 사진", type=["jpg", "jpeg", "png", "webp"], key="mdl_up")
        _msel = st.multiselect("만들 모델컷", list(image_gen.MODEL_PROMPTS.keys()),
                               default=["여성 모델 전신"], key="mdl_sel")
        _mdl_dir = st.text_input("🎬 연출 지시(선택)", placeholder="예: 얼굴 클로즈업 / 야외 햇살 / 정면 포즈", key="mdl_dir")
        _mdl_add = st.checkbox("✅ 생성 결과를 상세페이지에 추가", value=True, key="mdl_add_detail")
        if st.button("모델 착용컷 생성", key="mdl_btn"):
            _mref, _merr = None, None
            if _msrc == "사진 업로드":
                if _mup is not None:
                    _mref = _mup.getvalue()
            elif _msrc == "도매꾹 썸네일":
                _msp = st.session_state.get("sourcing_pick") or {}
                _mtu = _msp.get("thumb", "")
                if _mtu:
                    try:
                        _mref = image_gen.fetch_image_bytes(_mtu)
                    except Exception as _e:
                        _merr = str(_e)
            else:
                _mh = (st.session_state.get("copy_result") or {}).get("hero", "")
                if isinstance(_mh, str) and _mh.startswith("data:image"):
                    import base64 as _b64m
                    try:
                        _mref = _b64m.b64decode(_mh.split(",", 1)[1])
                    except Exception as _e:
                        _merr = str(_e)
            if not _mref:
                st.warning("기준 이미지를 찾을 수 없습니다. 사진을 업로드하거나 ②에서 상품을 선택하세요."
                           + (" (" + _merr + ")" if _merr else ""))
            elif not (use_real and (image_gen.available_gemini() or image_gen.available_openai())):
                st.info("실데이터 OFF 또는 이미지 키 없음 → 생성 불가")
            elif not _msel:
                st.warning("만들 모델컷을 1개 이상 선택하세요.")
            else:
                st.image(_mref, caption="기준 상품 사진", width=180)
                with st.spinner(str(len(_msel)) + "개 모델컷 생성 중…"):
                    _mres = image_gen.expand_models(_mref, _msel, provider=_mprov, direction=_mdl_dir.strip())
                _mcols = st.columns(2)
                for _mi, (_mn, _mb64, _meng2, _merr2) in enumerate(_mres):
                    with _mcols[_mi % 2]:
                        if _mb64:
                            _mdata = image_gen.b64_to_bytes(_mb64)
                            st.image(_mdata, caption=_mn + " · " + str(_meng2))
                            st.download_button("저장", _mdata, "model_" + _mn + ".png", "image/png", key="mdl_dl_" + str(_mi))
                            if _mdl_add:
                                _add_detail_image(_mb64)
                        else:
                            st.error(_mn + " 실패: " + str(_merr2))
        st.caption("※ 사람·얼굴이 생성됩니다. 실제 상품과 다를 수 있어, 정확한 착용감은 실사 촬영을 권장합니다.")
    with st.expander("🎬 상품 영상 생성 (베타 · fal.ai Kling)", expanded=False):
        if not video_gen.available():
            st.info("FAL_KEY가 .env에 없습니다. fal.ai 키를 넣으면 영상 생성이 활성화됩니다.")
        else:
            st.caption("⚠️ 영상은 유료입니다(모델·길이에 따라 5초 한 편 수백~천원대). 생성에 1~3분 걸리니 창을 닫지 마세요.")
            _vsrc = st.radio("기준 이미지", ["③ 대표이미지", "도매꾹 썸네일", "사진 업로드"],
                             horizontal=True, key="vid_src")
            _vup = None
            if _vsrc == "사진 업로드":
                _vup = st.file_uploader("상품 사진", type=["jpg", "jpeg", "png", "webp"], key="vid_up")
            _vmodel = st.selectbox("모델", list(video_gen.MODELS.keys()), key="vid_model")
            _vdur = st.radio("길이(초)", ["5", "10"], horizontal=True, key="vid_dur", help="길수록 비쌉니다")
            _vprompt = st.text_area("영상 연출 프롬프트 (영어 권장)", value=video_gen.DEFAULT_PROMPT,
                                    key="vid_prompt", height=80)
            if st.button("🎬 영상 생성", key="vid_btn", type="primary"):
                _vbytes, _verr = None, None
                if _vsrc == "사진 업로드":
                    if _vup is not None:
                        _vbytes = _vup.getvalue()
                elif _vsrc == "③ 대표이미지":
                    _hero = (st.session_state.get("copy_result") or {}).get("hero", "")
                    if isinstance(_hero, str) and _hero.startswith("data:image"):
                        import base64 as _b64v
                        try:
                            _vbytes = _b64v.b64decode(_hero.split(",", 1)[1])
                        except Exception as _e:
                            _verr = str(_e)
                else:
                    _spv = st.session_state.get("sourcing_pick") or {}
                    _tu = _spv.get("thumb", "")
                    if _tu:
                        try:
                            _vbytes = image_gen.fetch_image_bytes(_tu)
                        except Exception as _e:
                            _verr = str(_e)
                if not _vbytes:
                    st.warning("기준 이미지를 찾을 수 없습니다. ③에서 대표이미지를 만들거나 사진을 업로드하세요."
                               + (" (" + _verr + ")" if _verr else ""))
                else:
                    st.image(_vbytes, caption="기준 이미지", width=200)
                    _vlog = st.empty()
                    with st.spinner("영상 생성 중… 1~3분 걸립니다(창을 닫지 마세요)"):
                        _vurl, _veng, _vwarn = video_gen.generate_video(
                            image_bytes=_vbytes, prompt=_vprompt, duration=_vdur,
                            model=video_gen.MODELS[_vmodel],
                            on_log=lambda m: _vlog.caption(str(m)[:120]))
                    if _vurl:
                        st.session_state["product_video_url"] = _vurl
                        st.success("영상 생성 완료 · " + str(_veng))
                    else:
                        st.error("영상 생성 실패: " + str(_vwarn))
            _vu = st.session_state.get("product_video_url")
            if _vu:
                st.video(_vu)
                st.markdown("[⬇️ 영상(mp4) 열기/저장](" + _vu + ")")
                st.caption("스마트스토어 상세 HTML엔 영상이 안 들어갑니다 → 상품등록 시 '동영상' 등록란에 이 mp4를 올리세요.")
    cr = st.session_state.get("copy_result")
    dp = ""
    if cr:
        dp = f"Studio e-commerce hero shot for '{cr.get('title','product')}', clean white background, photorealistic, 1:1"
    prompt = st.text_area("이미지 프롬프트", value=dp, height=90)
    rm = st.checkbox("배경 제거(remove.bg)")
    if st.button("이미지 생성", type="primary"):
        if use_real and (image_gen.available_gemini() or image_gen.available_openai()):
            try:
                imgs, eng = image_gen.generate_image(prompt)
                st.caption('이미지 엔진: ' + eng)
                for b64 in imgs:
                    data = image_gen.b64_to_bytes(b64)
                    if rm and image_gen.available_removebg():
                        try:
                            data = image_gen.remove_background(data)
                        except Exception as e:
                            st.warning(f"배경제거 실패: {e}")
                    st.image(data, caption=eng)
                    st.download_button("이미지 저장", data, "product.png", "image/png")
            except Exception as e:
                st.error(f"이미지 생성 실패: {e}")
        else:
            st.info("실데이터 OFF 또는 이미지 키 없음 → 모의 표시")
            svg = "<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><rect width='100%' height='100%' fill='#f0f0f0'/><text x='50%' y='50%' text-anchor='middle' fill='#888'>MOCK IMAGE</text></svg>"
            st.image("data:image/svg+xml;utf8," + svg)
    st.caption("제품 본컷은 실사 권장 · AI는 연출/배경/인포그래픽 용도")


# ----- 5 배치 & 저장함
def _safe_rerun():
    fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if fn:
        fn()

with t5:
    st.subheader("📦 배치 & 저장함")
    st.markdown("#### 여러 개 연속 생성 (배치)")
    _batch_items = []
    _sdf = st.session_state.get("src_df")
    if _sdf is not None and not _sdf.empty and "상품후보" in _sdf.columns:
        _sel_a = st.multiselect("② 소싱 결과에서 선택", _sdf["상품후보"].tolist(), key="batch_src_sel")
        _bkw = st.session_state.get("sourcing_seed") or (st.session_state.get("kw_selected") or [""])[0]
        for _name in _sel_a:
            _r = _sdf[_sdf["상품후보"] == _name]
            _thumb = str(_r.iloc[0].get("썸네일") or "") if not _r.empty else ""
            _batch_items.append({"키워드": _bkw, "상품명": _name, "썸네일": _thumb})
    else:
        st.caption("② 소싱 검색을 먼저 하면 결과에서 골라 배치에 넣을 수 있습니다.")
    _manual = st.text_area("수동 목록 (한 줄당:  키워드 | 상품명 | 특징)", height=110,
                           placeholder="여름양말 | 시스루 발목양말 | 통기성\n14K귀걸이 | 데일리 링귀걸이",
                           key="batch_manual")
    _batch_items = _batch_items + batch.parse_manual(_manual)
    _bo1, _bo2, _bo3, _bo4 = st.columns(4)
    _b_13 = _bo1.checkbox("13섹션", value=True, key="b_mode13")
    _b_hu = _bo2.checkbox("문체정리", value=False, key="b_human")
    _b_img = _bo3.checkbox("대표이미지", value=False, key="b_img")
    _b_workers = _bo4.slider("동시 워커", 1, 3, 2, key="b_workers")
    st.caption(f"생성 대기 항목: {len(_batch_items)}건  ·  LLM: {'Claude' if provider == 'anthropic' else 'GPT'}  ·  실패는 건너뜀")
    if st.button("🚀 일괄 생성", type="primary", key="batch_run"):
        if not _batch_items:
            st.warning("생성할 항목이 없습니다. ② 선택 또는 수동 목록을 입력하세요.")
        elif not use_real:
            st.warning("실데이터 사용(API 호출)이 꺼져 있습니다. 사이드바에서 켜주세요.")
        else:
            with st.spinner(f"{len(_batch_items)}건 일괄 생성 중… (동시 {_b_workers}개)"):
                _results = batch.run_batch(_batch_items,
                    opts={"mode_13": _b_13, "do_human": _b_hu, "include_img": _b_img,
                          "use_thumb_img": True, "save": True, "provider": provider},
                    max_workers=_b_workers)
            _okc = sum(1 for _r in _results if _r["status"] == "ok")
            st.success(f"완료: 성공 {_okc} / 실패 {len(_results) - _okc}  ·  저장함에 추가됨")
            for _r in _results:
                if _r["status"] == "ok":
                    st.markdown(f"- ✅ **{_r['title']}**  ·  저장 id `{_r['id']}`")
                else:
                    st.markdown(f"- ❌ {_r.get('product') or _r.get('keyword') or '(이름없음)'}  ·  {_r.get('error')}")
    st.divider()
    st.markdown("#### 저장함")
    _saved = store.list_saved()
    if not _saved:
        st.info("아직 저장된 상세페이지가 없습니다. ③에서 '💾 이 상세페이지 저장'을 눌러 보관하세요.")
    else:
        st.caption(f"총 {len(_saved)}건 (최신순)")
        for _it in _saved:
            _icon = "🖼️" if _it["has_image"] else "📄"
            with st.expander(f"{_icon} {_it['title']}  ·  {_it['created']}"):
                st.caption(f"키워드: {_it.get('keyword','') or '-'}  |  id: {_it['id']}")
                _d = store.load_detail(_it["id"])
                bcol1, bcol2, bcol3 = st.columns([1, 1, 1])
                if bcol1.button("미리보기", key=f"prev_{_it['id']}"):
                    if _d and _d.get("html"):
                        components.html(_d["html"], height=600, scrolling=True)
                    else:
                        st.info("저장된 HTML이 없습니다.")
                if _d and _d.get("html"):
                    bcol2.download_button("HTML 다운로드", _d["html"].encode("utf-8"),
                                          f"{_it['id']}.html", "text/html", key=f"dl_{_it['id']}")
                if bcol3.button("🗑 삭제", key=f"del_{_it['id']}"):
                    if store.delete_detail(_it["id"]):
                        st.success("삭제됨.")
                        _safe_rerun()
                    else:
                        st.error("삭제 실패")
                if st.button("✏️ ③로 불러와 수정", key=f"edit_{_it['id']}"):
                    _d2 = store.load_detail(_it["id"])
                    if _d2:
                        _cr2 = dict(_d2.get("copy") or {})
                        if _d2.get("hero_path"):
                            try:
                                import base64 as _b64
                                with open(_d2["hero_path"], "rb") as _hf:
                                    _cr2["hero"] = "data:image/png;base64," + _b64.b64encode(_hf.read()).decode()
                            except Exception:
                                pass
                        st.session_state["copy_result"] = _cr2
                        st.session_state["editing_saved_id"] = _it["id"]
                        st.session_state["edit_nonce"] = st.session_state.get("edit_nonce", 0) + 1
                        st.session_state["pr_pending"] = (_d2.get("meta") or {}).get("상품명") or _cr2.get("title", "")
                        st.success("③ 상세페이지 탭에서 불러왔습니다. ③로 이동해 수정 후 '덮어쓰기 저장'을 누르세요.")
                        _safe_rerun()
                with st.expander("🛒 스마트스토어 임시저장 업로드 (미리보기)"):
                    if not commerce.available():
                        st.caption("커머스API 키(NAVER_COMMERCE_*)가 없어 업로드를 사용할 수 없습니다.")
                    else:
                        _uc1, _uc2, _uc3 = st.columns(3)
                        _u_cat = _uc1.text_input("카테고리코드", key=f"cat_{_it['id']}", placeholder="예: 50000167")
                        _u_price = _uc2.number_input("판매가(원)", min_value=0, step=100, value=0, key=f"price_{_it['id']}")
                        _u_stock = _uc3.number_input("재고", min_value=0, step=1, value=100, key=f"stock_{_it['id']}")
                        _has_img = bool(_d and _d.get("hero_path"))
                        _u_inp = {
                            "name": _it["title"],
                            "leafCategoryId": _u_cat,
                            "salePrice": _u_price,
                            "stockQuantity": _u_stock,
                            "detailContent": (_d or {}).get("html", ""),
                            "representativeImageUrl": "(전송 시 자동 업로드)" if _has_img else "",
                        }
                        if st.button("미리보기(dry-run)", key=f"dry_{_it['id']}"):
                            _miss = commerce.validate_inputs(_u_inp)
                            if _miss:
                                st.warning("입력/준비 필요: " + ", ".join(_miss))
                            else:
                                _payload = commerce.build_payload(_u_inp, status_type="WAIT")
                                st.success("등록 페이로드 미리보기 — 실제 전송 안 함 (statusType=WAIT, 판매대기)")
                                st.json(_payload)
                        st.markdown("---")
                        _confirm = st.checkbox("실제 업로드 확인 — 내 스마트스토어에 '판매대기'로 등록", key=f"confirm_{_it['id']}")
                        if st.button("🚀 스마트스토어에 업로드 (판매대기)", key=f"upload_{_it['id']}", disabled=not _confirm):
                            _miss = commerce.validate_inputs({**_u_inp, "representativeImageUrl": "x" if _has_img else ""})
                            if not _has_img:
                                st.error("대표이미지가 없는 항목입니다. ③에서 대표이미지를 만들어 저장한 항목만 업로드됩니다.")
                            elif _miss:
                                st.warning("입력 필요: " + ", ".join(_miss))
                            else:
                                with st.spinner("토큰 발급 → 이미지 업로드 → 상품 등록(판매대기) 중…"):
                                    try:
                                        _tok = commerce.get_token()
                                        with open(_d["hero_path"], "rb") as _hf:
                                            _imgurls = commerce.upload_image(_hf.read(), _tok)
                                        _pl = commerce.build_payload(
                                            {**_u_inp, "representativeImageUrl": _imgurls[0],
                                             "optionalImageUrls": _imgurls[1:]}, status_type="WAIT")
                                        _res = commerce.register_product(_pl, _tok)
                                        st.success("업로드 완료 — 판매자센터에서 '판매대기' 상태로 확인하세요.")
                                        st.json(_res)
                                    except Exception as _ue:
                                        st.error(f"업로드 실패: {_ue}")
                        st.caption("※ 'WAIT(판매대기)'로만 등록됩니다 — 고객 노출 전, 판매자센터에서 확인 후 직접 '판매중'으로 전환하세요.")
