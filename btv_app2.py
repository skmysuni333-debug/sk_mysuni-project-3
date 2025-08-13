import streamlit as st
import requests, json, re

AI_SERVICE_URL = "https://hook.eu2.make.com/wo7ggj9ex4ppxnv3l24m8jtlw0syd7a1"

st.set_page_config(layout="centered", page_title="배너 문구 자동 생성기")
st.title("🎬 영화 배너 문구 자동 생성기")
st.markdown("---")
st.markdown("영화 제목과 이벤트 유무·내용을 입력하면 AI가 자동으로 문구를 생성합니다.")
st.header("1. 영화 정보 입력")

# 안전 초기화
st.session_state.setdefault("movie_title", "")
st.session_state.setdefault("event_status", "없음")
st.session_state.setdefault("event_content", "")

st.text_input(
    "영화 제목을 입력하세요:",
    value=st.session_state.movie_title,
    placeholder="예: 범죄도시4",
    key="movie_title"
)

st.selectbox(
    "진행 중인 이벤트:",
    ("있음", "없음"),
    index=0 if st.session_state.event_status == "있음" else 1,
    key="event_status",
    help="콘텐츠 구매 시 진행 중인 할인·쿠폰·경품 등"
)

if st.session_state.event_status == "있음":
    st.text_input(
        "이벤트 내용 (예: 50% 할인쿠폰)",
        value=st.session_state.event_content,
        placeholder="이벤트가 '있음'이면 구체적으로 입력",
        key="event_content"
    )
else:
    st.session_state.event_content = ""

col1, col2 = st.columns(2)
with col1:
    generate_button = st.button("배너 문구 생성하기")
with col2:
    reset_button = st.button("다시 쓰기")

st.markdown("---")

if reset_button:
    for k in ("movie_title", "event_status", "event_content"):
        st.session_state.pop(k, None)
    st.rerun()

# -------------------------------
# ✅ 세트 자동 분리 (모든 포맷 통합 처리)
# -------------------------------
def split_sets_smart(text: str):
    """---, '- 소구포인트:' 시작, 빈 줄로 구분된 블록까지 자동 분리"""
    if not text:
        return []
    s = text.replace("\r\n", "\n").replace("\r", "\n").strip()

    # 1) --- 구분자
    if '---' in s:
        parts = [p.strip() for p in re.split(r'\n?\s*---\s*\n?', s)]
        return [p for p in parts if p]

    # 2) '- 소구포인트:' 블록 반복
    pattern = re.compile(r'(?m)^(?:-?\s*소구포인트\s*:\s*)')
    starts = [m.start() for m in pattern.finditer(s)]
    if len(starts) > 1:
        chunks = []
        for i, st_idx in enumerate(starts):
            end_idx = starts[i+1] if i+1 < len(starts) else len(s)
            block = s[st_idx:end_idx].strip()
            if block:
                chunks.append(block)
        return chunks

    # 3) 빈 줄 여러 개로 구분
    parts = [p.strip() for p in re.split(r'\n\s*\n\s*\n+', s)]
    if len(parts) > 1:
        return [p for p in parts if p]

    # 못 나누면 전체를 한 세트로
    return [s]
# -------------------------------
# ✅ 블록에서 '소구포인트' 라벨을 제목으로 추출
# -------------------------------
def set_title_from_block(block: str) -> str:
    """
    세트 블록 안의 라벨을 제목으로 사용.
    지원 패턴:
      - '소구포인트: 값'
      - '- 소구포인트: 값'
      - '[선정 소구포인트]: 값'
    """
    if not block:
        return ""
    s = block.replace("\r\n", "\n").replace("\r", "\n")
    patterns = [
        r'(?im)^\s*\[\s*선정\s*소구포인트\s*\]\s*:\s*(.+?)\s*$',
        r'(?im)^\s*-\s*소구포인트\s*:\s*(.+?)\s*$',
        r'(?im)^\s*소구포인트\s*:\s*(.+?)\s*$',
    ]
    for pat in patterns:
        m = re.search(pat, s, flags=re.MULTILINE)
        if m:
            title = m.group(1).strip()
            # 맨 끝 괄호 부연(예: (23자)) 제거
            title = re.sub(r'\s*\([^)]*\)\s*$', '', title).strip()
            return title
    return ""
# -------------------------------
# ✅ Webhook 응답에서 필드 안전 추출
# -------------------------------
def extract_render_field(result, key: str) -> str:
    """result → result['render'] → result['data']['render'] 순서로 안전 추출"""
    data = result

    # 0) 문자열(JSON 텍스트)면 다시 파싱
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return ""

    # 1) 최상위에서 바로 찾기
    if isinstance(data, dict) and key in data:
        return data.get(key) or ""

    # 2) render 블록에서 찾기
    if isinstance(data, dict):
        render = data.get("render")
        if isinstance(render, dict) and key in render:
            return render.get(key) or ""

    # 3) data.render 블록에서 찾기
    if isinstance(data, dict):
        data_blk = data.get("data")
        if isinstance(data_blk, dict):
            render = data_blk.get("render")
            if isinstance(render, dict) and key in render:
                return render.get(key) or ""

    return ""

# -------------------------------
# 🚀 생성 버튼 클릭 처리
# -------------------------------
if generate_button:
    if not st.session_state.movie_title.strip():
        st.warning("영화 제목을 입력해주세요!")
    else:
        with st.spinner("AI가 영화 정보를 분석하고 문구를 생성 중입니다..."):
            try:
                payload = {
                    "movie_title": st.session_state.movie_title,
                    "event_status": st.session_state.event_status,
                    "event_content": st.session_state.event_content,
                }
                resp = requests.post(
                    AI_SERVICE_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=250,
                )

                # HTTP 에러 검사
                resp.raise_for_status()

                # JSON 파싱 (문자열 응답도 대비)
                try:
                    result = resp.json()
                except json.JSONDecodeError:
                    # 서버가 문자열로 줄 수도 있으니 원문 보관
                    result = resp.text

                  # ✅ 소구포인트 + 배너문구 추출
                points_text = extract_render_field(result, "c_points_cell")
                big_text  = extract_render_field(result, "d_big_cell")
                long_text = extract_render_field(result, "e_long_cell")
                two_text  = extract_render_field(result, "f_two_col_cell")

                # 한 칸 = 한 세트
                points_sets = split_sets_smart(points_text)
                big_sets  = split_sets_smart(big_text)
                long_sets = split_sets_smart(long_text)
                two_sets  = split_sets_smart(two_text)

                st.header("2. 생성된 배너 문구")
                with st.expander("소구포인트", expanded=True):
                    if not points_sets:
                        st.info("소구포인트가 없습니다.")
                    else:
                        st.markdown("\n".join(points_sets))

                tab1, tab2, tab3 = st.tabs(["빅배너", "롱배너", "2단 배너"])

                with tab1:
                    if not big_sets:
                        st.info("빅배너 문구가 없습니다.")
                    else:
                        for i, block in enumerate(big_sets, 1):
                            title = set_title_from_block(block) or f"세트 {i}"
                            st.subheader(title)
                            st.text_area(
                                f"big_set_{i}", block, height=160,
                                key=f"out_big_{i}", label_visibility="collapsed"
                            )

                with tab2:
                    if not long_sets:
                        st.info("롱배너 문구가 없습니다.")
                    else:
                        for i, block in enumerate(long_sets, 1):
                            title = set_title_from_block(block) or f"세트 {i}"
                            st.subheader(title)
                            st.text_area(
                                f"long_set_{i}", block, height=160,
                                key=f"out_long_{i}", label_visibility="collapsed"
                            )

                with tab3:
                    if not two_sets:
                        st.info("2단 배너 문구가 없습니다.")
                    else:
                        for i, block in enumerate(two_sets, 1):
                            title = set_title_from_block(block) or f"세트 {i}"
                            st.subheader(title)
                            st.text_area(
                                f"two_set_{i}", block, height=160,
                                key=f"out_two_{i}", label_visibility="collapsed"
                            )

                st.success("문구 생성이 완료되었습니다! 🙂")

            except requests.exceptions.ConnectionError:
                st.error("AI 서비스에 연결할 수 없습니다. Make 시나리오가 실행 중인지 확인해주세요.")
            except requests.exceptions.Timeout:
                st.error("요청이 시간 초과되었습니다. Make 처리 시간을 확인해주세요.")
            except requests.HTTPError as e:
                st.error(f"서버 오류: {e}")
            except Exception as e:
                st.error(f"예상치 못한 오류가 발생했습니다: {e}")








