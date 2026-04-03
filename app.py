import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import base64
import io

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="학원 성적표 v2",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.stApp { background: #f5f7fa; }
.metric-pill {
    display: inline-block; padding: 6px 16px;
    border-radius: 20px; font-size: 13px; font-weight: 700; margin: 4px;
}
.pill-green  { background:#e8f5e9; color:#2e7d32; }
.pill-blue   { background:#e3f2fd; color:#1565c0; }
.pill-orange { background:#fff3e0; color:#e65100; }
.pill-red    { background:#fce4ec; color:#c62828; }
.stButton > button { border-radius: 10px; font-weight: 700; }
div[data-testid="stSidebar"] { background: #1a237e; }
div[data-testid="stSidebar"] * { color: white !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏫 학원 정보")
    academy_name   = st.text_input("학원명",       value="클로드 수학학원")
    teacher_name   = st.text_input("담당 선생님",   value="김지훈 선생님")
    class_name     = st.text_input("반 이름",       value="초등 5학년 심화반")
    report_month   = st.selectbox("평가 월", [f"{m}월" for m in range(1, 13)],
                                   index=datetime.now().month - 1)
    st.markdown("---")
    st.markdown("## 👤 학생 정보")
    student_name   = st.text_input("학생 이름",    value="홍길동")
    student_school = st.text_input("재학 학교",    value="서울초등학교")
    student_grade  = st.selectbox("학년", ["초등 3학년","초등 4학년","초등 5학년","초등 6학년",
                                           "중학교 1학년","중학교 2학년","중학교 3학년"])
    st.markdown("---")
    st.markdown("## 🤖 AI 코멘트 설정")
    ai_mode = st.radio("코멘트 생성 방식",
                        ["📝 규칙 기반 (무료)", "🧠 Claude AI (유료·고품질)"],
                        index=0)
    claude_key = ""
    if "Claude" in ai_mode:
        claude_key = st.text_input("Anthropic API Key", type="password",
                                    placeholder="sk-ant-...")
        st.caption("💳 성적표 1건당 약 ₩4~15원 (이미지 분석 포함 시)")

# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────
st.markdown(
    f"# 📊 학원 성적표 v2 &nbsp;<span style='font-size:16px;color:#888;font-weight:400'>{academy_name}</span>",
    unsafe_allow_html=True
)

tab_input, tab_preview = st.tabs(["✏️ 성적 입력", "📋 성적표 미리보기 & 출력"])

# ══════════════════════════════════════════════
# TAB 1 : 성적 입력
# ══════════════════════════════════════════════
with tab_input:

    # ── [NEW] 시험지 업로드 ──────────────────────
    with st.container(border=True):
        st.markdown("### 📎 시험지 / 성적표 파일 업로드 (선택)")
        st.caption("이미지(jpg·png) 또는 PDF를 올리면 Claude AI가 문항별 내용을 읽고 코멘트에 반영합니다. "
                   "파일 없이 아래 수동 입력만으로도 성적표를 만들 수 있습니다.")
        uploaded_files = st.file_uploader(
            "파일 선택 (여러 장 가능)",
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)}개 파일 업로드 완료 — Claude AI 모드에서 자동 분석됩니다.")
            cols = st.columns(min(len(uploaded_files), 4))
            for i, f in enumerate(uploaded_files):
                if f.type.startswith("image"):
                    cols[i % 4].image(f, caption=f.name, use_container_width=True)
                else:
                    cols[i % 4].markdown(f"📄 `{f.name}`")

    st.markdown("")

    # ── 점수 입력 + 성적 추이 ──────────────────
    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        with st.container(border=True):
            st.markdown("### 📝 이번 달 점수")
            student_score = st.number_input("학생 종합 점수 (점)", 0, 100, 85, 1)
            class_avg     = st.number_input("반 평균 점수 (점)",   0, 100, 76, 1)
            subject       = st.text_input("학습 단원/과목", value="분수와 소수의 혼합 계산")
            st.markdown("#### 🎯 5대 평가 지표 (0~100)")
            m1 = st.slider("수업태도",       0, 100, 88)
            m2 = st.slider("과제수행",       0, 100, 82)
            m3 = st.slider("계산력(연산)",   0, 100, 90)
            m4 = st.slider("심화문제풀이",   0, 100, 72)
            m5 = st.slider("학업성취도",     0, 100, 85)

    with col_right:
        with st.container(border=True):
            st.markdown("### 📈 분기별 성적 추이")
            q_labels = ["1분기", "2분기", "3분기", "4분기(현재)"]
            q_scores = []
            for i, q in enumerate(q_labels):
                default = [70, 76, 80, student_score][i]
                val = st.number_input(q, 0, 100, default, 1, key=f"q{i}")
                q_scores.append(val)
            st.markdown("#### 📌 강사 메모")
            memo = st.text_area("담당 강사 메모 (선택)",
                                 value="분수 나눗셈 역수 개념 정착 확인. 심화문제 3번 패턴 반복 오류 있음.",
                                 height=140,
                                 label_visibility="collapsed")

    st.markdown("")
    gen_btn = st.button("🚀 성적표 생성하기", use_container_width=True, type="primary")

    if gen_btn:
        # 파일 → bytes 직렬화 (session_state 저장용)
        files_data = []
        for f in (uploaded_files or []):
            files_data.append({"name": f.name, "type": f.type, "bytes": f.getvalue()})

        st.session_state["report_data"] = dict(
            academy_name=academy_name, teacher_name=teacher_name,
            class_name=class_name,    report_month=report_month,
            student_name=student_name, student_school=student_school,
            student_grade=student_grade,
            student_score=student_score, class_avg=class_avg,
            subject=subject,
            metrics={"수업태도": m1, "과제수행": m2, "계산력(연산)": m3,
                     "심화문제풀이": m4, "학업성취도": m5},
            q_scores=q_scores, q_labels=q_labels,
            memo=memo,
            ai_mode=ai_mode, claude_key=claude_key,
            files_data=files_data,
        )
        st.success("✅ 완료! '📋 성적표 미리보기 & 출력' 탭을 클릭하세요.")

# ══════════════════════════════════════════════
# TAB 2 : 미리보기 & 출력
# ══════════════════════════════════════════════
with tab_preview:

    if "report_data" not in st.session_state:
        st.info("✏️ '성적 입력' 탭에서 데이터를 입력하고 '성적표 생성하기'를 눌러주세요.")
        st.stop()

    d = st.session_state["report_data"]

    # ── 코멘트 생성 ───────────────────────────
    def rule_based_comment(d: dict) -> str:
        s, avg = d["student_score"], d["class_avg"]
        m, diff = d["metrics"], s - avg
        subj, grade = d["subject"], d["student_grade"]

        if "분수" in subj or "소수" in subj:
            p1 = (f"이번 달 학습 단원인 '{subj}'은(는) {grade} 수학 과정의 핵심 개념으로, "
                  f"분수·소수의 관계 이해와 사칙연산 응용 능력을 동시에 요구합니다. "
                  f"이 단원은 중학교 1학년 유리수·방정식의 직접적인 기초가 되므로 "
                  f"연산 정확도와 개념 이해를 균형 있게 갖추는 것이 목표입니다.")
        elif "도형" in subj or "넓이" in subj or "부피" in subj:
            p1 = (f"이번 달 학습 단원인 '{subj}'은(는) 공간 감각과 수리 논리를 함께 훈련합니다. "
                  f"초등 도형 학습은 중학교 기하(합동·닮음·피타고라스)의 초석이 되므로 "
                  f"공식 암기보다 원리 이해 중심으로 지도하고 있습니다.")
        else:
            p1 = (f"이번 달 학습 단원인 '{subj}'은(는) {grade} 수학 과정의 주요 주제로 "
                  f"논리적 사고력과 계산 정확도를 함께 요구합니다. "
                  f"이후 상급 학년의 기초 개념으로 연결되므로 원리 이해 중심 학습이 중요합니다.")

        weak   = [k for k, v in m.items() if v < 75]
        strong = [k for k, v in m.items() if v >= 90]
        obs = []
        if diff >= 10:
            obs.append(f"{d['student_name']} 학생은 반 평균 대비 {diff:+d}점으로 우수한 성취를 보였습니다.")
        elif diff >= 0:
            obs.append(f"이번 달 종합 점수는 반 평균보다 {diff:+d}점으로 평균 수준의 성취를 유지하고 있습니다.")
        else:
            obs.append(f"종합 점수가 반 평균보다 {diff}점 낮아 집중 보완이 필요합니다.")
        if strong:
            obs.append(f"특히 {', '.join(strong)} 영역에서 90점 이상의 역량을 보였습니다.")
        if weak:
            obs.append(f"반면 {', '.join(weak)} 영역(75점 미만)은 추가 보완이 필요합니다.")
        if d["memo"]:
            obs.append(f"수업 중 관찰: {d['memo']}")
        p2 = " ".join(obs)

        qs = d["q_scores"]
        if qs[-1] > qs[-2]:
            tmsg = f"지난 분기 대비 {qs[-1]-qs[-2]:+d}점 향상된 긍정적인 흐름입니다."
        elif qs[-1] < qs[-2]:
            tmsg = f"지난 분기 대비 {qs[-1]-qs[-2]}점 하락하였으나 개념 보완으로 회복 가능합니다."
        else:
            tmsg = "꾸준한 학습 흐름을 유지하고 있습니다."
        p3 = (f"{tmsg} 다음 달에는 {subj} 응용 문제 확장 및 이전 단원 연계 복습을 병행할 예정입니다. "
              f"가정 내 학습 루틴을 꾸준히 유지해 주시면 더욱 좋은 결과를 기대할 수 있습니다.")

        return f"{p1}\n\n{p2}\n\n{p3}"

    def claude_ai_comment(d: dict) -> str:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=d["claude_key"])
            metrics_str = "\n".join(f"  - {k}: {v}점" for k, v in d["metrics"].items())

            content = []

            # 업로드된 시험지 이미지 첨부
            for fd in d.get("files_data", []):
                if "image" in fd["type"]:
                    b64 = base64.b64encode(fd["bytes"]).decode()
                    content.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": fd["type"], "data": b64},
                    })
                    content.append({
                        "type": "text",
                        "text": f"위 이미지는 '{fd['name']}' 시험지입니다. 문항별 오답 패턴과 풀이 흔적을 분석해 주세요."
                    })

            content.append({"type": "text", "text": f"""당신은 수학 전문 학원 강사입니다. 아래 데이터와 첨부된 시험지를 종합하여 학부모 상담용 성적 진단 리포트를 작성하십시오.

[학생 정보]
- 이름: {d['student_name']} ({d['student_grade']})
- 학습 단원: {d['subject']}
- 이번 달 점수: {d['student_score']}점 (반 평균: {d['class_avg']}점)
- 5대 평가 지표:
{metrics_str}
- 분기별 성적: {dict(zip(d['q_labels'], d['q_scores']))}
- 강사 메모: {d['memo']}

[작성 규칙]
- 미사여구 없이 사실 기반, 교육 컨설턴트 톤
- 반드시 3문단 구조:
  1문단: 학습 단원 핵심 개념 + 상급 과정 연계성 (4~5줄)
  2문단: 시험지 분석 포함 학생 학습 습관·강점·보완점 (4~5줄)
  3문단: 다음 달 진도 계획 + 가정 연계 제안 (3~4줄)

JSON이나 코드 없이 순수 텍스트 3문단만 출력하십시오."""})

            msg = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=800,
                messages=[{"role": "user", "content": content}],
            )
            return msg.content[0].text
        except Exception as e:
            return f"[Claude AI 오류: {e}]\n\n" + rule_based_comment(d)

    with st.spinner("코멘트 생성 중..."):
        use_claude = "Claude" in d["ai_mode"] and d["claude_key"]
        comment_text = claude_ai_comment(d) if use_claude else rule_based_comment(d)

    # ── 색상 상수 ─────────────────────────────
    BLUE   = "#1a237e"
    BLUE2  = "#3949ab"
    SILVER = "#90a4ae"
    ORANGE = "#e65100"

    # ── 차트 함수들 ───────────────────────────
    def make_bar(d):
        s, avg = d["student_score"], d["class_avg"]
        diff   = s - avg
        c_s    = BLUE2 if diff >= 0 else "#c62828"
        fig = go.Figure()
        fig.add_trace(go.Bar(name=d["student_name"], x=["종합 점수"], y=[s],
                             marker_color=c_s, width=0.25,
                             text=[f"<b>{s}점</b>"], textposition="outside",
                             textfont=dict(size=16, color=c_s)))
        fig.add_trace(go.Bar(name="반 평균", x=["종합 점수"], y=[avg],
                             marker_color=SILVER, width=0.25,
                             text=[f"<b>{avg}점</b>"], textposition="outside",
                             textfont=dict(size=16, color="#555")))
        sign = "+" if diff >= 0 else ""
        fig.add_annotation(x=0.5, y=max(s, avg) + 9, xref="paper", yref="y",
                           text=f"편차 {sign}{diff}점", showarrow=False,
                           font=dict(size=13, color=c_s),
                           bgcolor="white", bordercolor=c_s, borderwidth=1, borderpad=5)
        fig.update_layout(barmode="group", height=340,
                          margin=dict(l=10, r=10, t=30, b=10),
                          paper_bgcolor="white", plot_bgcolor="white",
                          yaxis=dict(range=[0, 118], showgrid=True, gridcolor="#f0f0f0",
                                     ticksuffix="점"),
                          xaxis=dict(showticklabels=False),
                          legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
                          font=dict(family="Noto Sans KR"))
        return fig

    def make_radar(d):
        cats = list(d["metrics"].keys())
        vals = list(d["metrics"].values())
        fig  = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=[100]*len(cats)+[100], theta=cats+[cats[0]],
            fill="toself", fillcolor="rgba(200,210,220,0.25)",
            line=dict(color="#cfd8dc", width=1), showlegend=False))
        fig.add_trace(go.Scatterpolar(
            r=vals+[vals[0]], theta=cats+[cats[0]],
            fill="toself", fillcolor="rgba(57,73,171,0.18)",
            line=dict(color=BLUE2, width=2.5),
            marker=dict(size=8, color=BLUE2, line=dict(width=2, color="white")),
            name=d["student_name"]))
        fig.update_layout(
            polar=dict(
                bgcolor="white",
                radialaxis=dict(visible=True, range=[0,100],
                                tickvals=[25,50,75,100],
                                tickfont=dict(size=9, color="#aaa"),
                                gridcolor="#e0e0e0", linecolor="#e0e0e0"),
                angularaxis=dict(tickfont=dict(size=12, color="#333",
                                               family="Noto Sans KR"),
                                 linecolor="#ccc")),
            height=340,
            margin=dict(l=55, r=55, t=30, b=30),
            paper_bgcolor="white",
            showlegend=False,
            font=dict(family="Noto Sans KR"))
        return fig

    def make_trend(d):
        labels, scores = d["q_labels"], d["q_scores"]
        avg_line = [d["class_avg"]] * len(labels)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=labels, y=avg_line, mode="lines",
                                  line=dict(color=SILVER, width=1.5, dash="dot"),
                                  name="반 평균"))
        fig.add_trace(go.Scatter(x=labels, y=scores, mode="lines+markers+text",
                                  line=dict(color=ORANGE, width=3),
                                  marker=dict(size=10, color=ORANGE,
                                              line=dict(width=2, color="white")),
                                  text=[f"<b>{s}점</b>" for s in scores],
                                  textposition="top center",
                                  textfont=dict(size=12, color=ORANGE),
                                  name=d["student_name"],
                                  fill="tozeroy", fillcolor="rgba(230,81,0,0.07)"))
        fig.update_layout(height=280,
                          margin=dict(l=10, r=10, t=20, b=10),
                          paper_bgcolor="white", plot_bgcolor="white",
                          yaxis=dict(range=[max(0, min(scores)-15), 110],
                                     showgrid=True, gridcolor="#f5f5f5",
                                     ticksuffix="점"),
                          xaxis=dict(tickfont=dict(size=12, family="Noto Sans KR")),
                          legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
                          font=dict(family="Noto Sans KR"))
        return fig

    # ── 헤더 배너 ────────────────────────────
    diff  = d["student_score"] - d["class_avg"]
    sign  = "+" if diff >= 0 else ""
    st.markdown(f"""
<div style="background:linear-gradient(135deg,{BLUE},{BLUE2});color:white;
            border-radius:14px;padding:26px 30px;margin-bottom:22px;">
  <div style="font-size:12px;opacity:.7;letter-spacing:2px;margin-bottom:4px;">
    {d['academy_name']} · {d['class_name']} · {d['report_month']} 성적표
  </div>
  <div style="font-size:28px;font-weight:900;letter-spacing:-0.5px;">
    {d['student_name']} 학생 월간 학업 성취 리포트
  </div>
  <div style="margin-top:7px;font-size:13px;opacity:.8;">
    {d['student_school']} | {d['student_grade']} | 담당: {d['teacher_name']}
  </div>
</div>""", unsafe_allow_html=True)

    # ── 요약 지표 3칸 ───────────────────────
    diff_color = BLUE2 if diff >= 0 else "#c62828"
    c1, c2, c3 = st.columns(3)
    for col, label, val, color in [
        (c1, "학생 종합 점수", f"{d['student_score']}점", BLUE2),
        (c2, "해당 과정 평균", f"{d['class_avg']}점", "#546e7a"),
        (c3, "성취도 편차",    f"{sign}{diff}점",         diff_color),
    ]:
        with col:
            with st.container(border=True):
                st.markdown(
                    f"<div style='text-align:center'>"
                    f"<div style='font-size:12px;color:#888;margin-bottom:4px'>{label}</div>"
                    f"<div style='font-size:40px;font-weight:900;color:{color}'>{val}</div>"
                    f"</div>",
                    unsafe_allow_html=True)

    st.markdown("")

    # ── [FIX] 막대 / 레이더 — 각각 독립 컨테이너 ──
    col_bar, col_radar = st.columns(2, gap="large")

    with col_bar:
        with st.container(border=True):
            st.markdown("#### 📊 종합 점수 비교")
            st.plotly_chart(make_bar(d), use_container_width=True,
                            config={"displayModeBar": False})

    with col_radar:
        with st.container(border=True):
            st.markdown("#### 🕸️ 5대 영역별 역량 분포")
            st.plotly_chart(make_radar(d), use_container_width=True,
                            config={"displayModeBar": False})

    # ── 성적 추이 (전체 폭) ─────────────────
    with st.container(border=True):
        st.markdown("#### 📈 분기별 성적 향상 추이")
        st.plotly_chart(make_trend(d), use_container_width=True,
                        config={"displayModeBar": False})

    # ── 5대 지표 뱃지 ───────────────────────
    with st.container(border=True):
        st.markdown("#### 🏷️ 5대 평가 지표")
        badges = ""
        for label, val in d["metrics"].items():
            cls = ("pill-blue" if val >= 90 else "pill-green" if val >= 75
                   else "pill-orange" if val >= 60 else "pill-red")
            badges += f'<span class="metric-pill {cls}">{label} {val}점</span>'
        st.markdown(badges, unsafe_allow_html=True)

    # ── 전문가 코멘트 ──────────────────────
    mode_label = "Claude AI 시험지 분석 포함" if (use_claude and d.get("files_data")) \
                 else "Claude AI 생성" if use_claude else "규칙 기반 생성"
    with st.container(border=True):
        st.markdown(
            f"#### 📝 교육 전문가 심층 진단 "
            f"<span style='font-size:11px;color:#aaa;'>({mode_label})</span>",
            unsafe_allow_html=True)
        for para in comment_text.split("\n\n"):
            if para.strip():
                st.markdown(f"> {para.strip()}")

    # ── 다운로드 ────────────────────────────
    def build_html(d, comment):
        # ── HTML 전용: width 고정으로 flex 넘침 방지 ──
        def _fix_width(fig, w, h):
            fig.update_layout(width=w, height=h, autosize=False)
            return fig

        bar_h   = _fix_width(make_bar(d),   650, 320).to_html(
                      full_html=False, include_plotlyjs="cdn",
                      config={"displayModeBar": False})
        radar_h = _fix_width(make_radar(d), 310, 290).to_html(
                      full_html=False, include_plotlyjs=False,
                      config={"displayModeBar": False})
        trend_h = _fix_width(make_trend(d), 310, 260).to_html(
                      full_html=False, include_plotlyjs=False,
                      config={"displayModeBar": False})

        diff   = d["student_score"] - d["class_avg"]
        sign   = "+" if diff >= 0 else ""
        dc     = "#1a237e" if diff >= 0 else "#c62828"

        rows = ""
        for label, val in d["metrics"].items():
            filled = int(val / 100 * 18)
            bar    = "█" * filled + "░" * (18 - filled)
            grade  = "우수" if val >= 90 else "양호" if val >= 75 else "보통" if val >= 60 else "미흡"
            gc     = "#1565c0" if val >= 90 else "#2e7d32" if val >= 75 else "#e65100" if val >= 60 else "#c62828"
            rows  += (f"<tr><td style='padding:8px 14px;font-weight:600'>{label}</td>"
                      f"<td style='padding:8px 14px;font-size:10px;color:#999;letter-spacing:-1px'>{bar}</td>"
                      f"<td style='padding:8px 14px;font-weight:700;color:#1a237e;text-align:right'>{val}점</td>"
                      f"<td style='padding:8px 14px;text-align:right'>"
                      f"<span style='background:{gc}22;color:{gc};padding:2px 8px;"
                      f"border-radius:10px;font-size:11px;font-weight:700'>{grade}</span></td></tr>")

        paras = "".join(
            f"<p style='margin:0 0 16px 0;text-indent:1em'>{p.strip()}</p>"
            for p in comment.split("\n\n") if p.strip()
        )

        return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:'Noto Sans KR',sans-serif; background:#eceff1; padding:20px; }}
@media print {{
  body {{ background:white; padding:0; }}
  .no-print {{ display:none !important; }}
  @page {{ size:A4 portrait; margin:0; }}
  .page {{ box-shadow:none !important; margin:0 !important; }}
}}
.page {{
  width:210mm; min-height:296mm; background:white;
  margin:0 auto 20px; padding:13mm 17mm;
  box-shadow:0 4px 20px rgba(0,0,0,0.12);
  page-break-after:always; position:relative;
}}
.page:last-child {{ page-break-after:auto; }}
.hdr {{ background:linear-gradient(135deg,#1a237e,#3949ab); color:white;
         border-radius:10px; padding:16px 22px; margin-bottom:18px; }}
.hdr .ac {{ font-size:10pt; opacity:.75; letter-spacing:1px; margin-bottom:3px; }}
.hdr .ti {{ font-size:18pt; font-weight:900; }}
.hdr .su {{ font-size:10pt; opacity:.8; margin-top:4px; }}
.sec {{ font-size:12pt; font-weight:800; color:#1a237e;
         border-left:5px solid #3949ab; padding-left:10px;
         margin:16px 0 10px; }}
.srow {{ display:flex; gap:10px; margin-bottom:16px; }}
.sbox {{ flex:1; text-align:center; border-radius:8px; padding:12px 8px;
          border:1.5px solid #e0e0e0; }}
.sbox .lb {{ font-size:9pt; color:#888; margin-bottom:4px; }}
.sbox .vl {{ font-size:24pt; font-weight:900; }}
table.mt {{ width:100%; border-collapse:collapse; background:#fafafa;
             border:1px solid #eee; border-radius:8px; overflow:hidden; }}
table.mt tr {{ border-bottom:1px solid #eee; }}
table.mt tr:last-child {{ border-bottom:none; }}
table.mt tr:nth-child(even) {{ background:#f5f7ff; }}
.cmt {{ font-size:11pt; line-height:2.0; color:#424242;
         border-top:4px solid #1a237e; padding-top:14px; }}
.ft {{ position:absolute; bottom:10mm; left:17mm; right:17mm;
        display:flex; justify-content:space-between;
        border-top:1px solid #e0e0e0; padding-top:6px;
        font-size:8.5pt; color:#aaa; }}
.pbtn {{ display:block; width:280px; margin:0 auto 18px;
          background:#1a237e; color:white; border:none;
          padding:14px 28px; border-radius:10px;
          font-size:15px; font-weight:700; cursor:pointer;
          font-family:'Noto Sans KR',sans-serif; }}
.pbtn:hover {{ background:#3949ab; }}
</style></head><body>
<button class="pbtn no-print" onclick="window.print()">🖨️ A4 인쇄 / PDF 저장</button>

<!-- PAGE 1 -->
<div class="page">
  <div class="hdr">
    <div class="ac">{d['academy_name']} · {d['class_name']} · {d['report_month']} 월간 성적표</div>
    <div class="ti">{d['student_name']} 학생 학업 성취 리포트</div>
    <div class="su">{d['student_school']} | {d['student_grade']} | 담당: {d['teacher_name']}</div>
  </div>
  <div class="srow">
    <div class="sbox"><div class="lb">학생 종합 점수</div>
      <div class="vl" style="color:#1a237e">{d['student_score']}점</div></div>
    <div class="sbox"><div class="lb">해당 과정 평균</div>
      <div class="vl" style="color:#546e7a">{d['class_avg']}점</div></div>
    <div class="sbox"><div class="lb">성취도 편차</div>
      <div class="vl" style="color:{dc}">{sign}{diff}점</div></div>
  </div>
  <div class="sec">📊 종합 점수 비교 (학생 vs 반 평균)</div>
  <div style="height:330px">{bar_h}</div>
  <div class="sec" style="margin-top:14px">🏷️ 5대 평가 지표 상세</div>
  <table class="mt">{rows}</table>
  <div class="ft"><span>{d['academy_name']}</span>
    <span>발행일 {datetime.now().strftime('%Y년 %m월 %d일')} · 1 / 2</span></div>
</div>

<!-- PAGE 2 -->
<div class="page">
  <div class="hdr">
    <div class="ac">{d['academy_name']} · 심층 분석</div>
    <div class="ti">{d['student_name']} 학생 — 역량 분석 & 성장 추이</div>
    <div class="su">학습 단원: {d['subject']}</div>
  </div>
  <div style="display:table;width:100%;table-layout:fixed;border-spacing:16px 0">
    <div style="display:table-cell;width:50%;vertical-align:top">
      <div class="sec">🕸️ 영역별 역량 분포</div>
      <div style="overflow:hidden">{radar_h}</div>
    </div>
    <div style="display:table-cell;width:50%;vertical-align:top">
      <div class="sec">📈 분기별 성적 추이</div>
      <div style="overflow:hidden">{trend_h}</div>
    </div>
  </div>
  <div class="sec" style="margin-top:16px">📝 교육 전문가 심층 진단</div>
  <div class="cmt">{paras}</div>
  <div class="ft"><span>{d['teacher_name']} 작성</span>
    <span>발행일 {datetime.now().strftime('%Y년 %m월 %d일')} · 2 / 2</span></div>
</div>
</body></html>"""

    st.markdown("---")
    html_out  = build_html(d, comment_text)
    b64       = base64.b64encode(html_out.encode("utf-8")).decode()
    fname     = f"성적표_{d['student_name']}_{d['report_month']}_{datetime.now().strftime('%m%d')}.html"

    col_dl, col_tip = st.columns([1, 2])
    with col_dl:
        st.markdown(
            f'<a href="data:text/html;base64,{b64}" download="{fname}" '
            f'style="display:block;background:#1a237e;color:white;text-align:center;'
            f'padding:14px;border-radius:10px;font-size:15px;font-weight:700;text-decoration:none;">'
            f'⬇️ HTML 성적표 다운로드</a>',
            unsafe_allow_html=True)
    with col_tip:
        st.info("💡 다운로드 → 브라우저에서 열기 → **⌘+P** → 'PDF로 저장' 선택\n\nA4 2페이지로 완벽하게 인쇄됩니다.")
