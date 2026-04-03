import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import base64
import json
import re
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

# ─────────────────────────────────────────────
# 전역 CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.stApp { background: #f5f7fa; }
.section-card {
    background: white; border-radius: 14px;
    padding: 24px 28px; margin-bottom: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    border: 1px solid #e8ecf0;
}
.metric-pill {
    display: inline-block; padding: 6px 16px;
    border-radius: 20px; font-size: 13px; font-weight: 700;
    margin: 4px;
}
.pill-green  { background:#e8f5e9; color:#2e7d32; }
.pill-blue   { background:#e3f2fd; color:#1565c0; }
.pill-orange { background:#fff3e0; color:#e65100; }
.pill-red    { background:#fce4ec; color:#c62828; }
.stButton > button { border-radius: 10px; font-weight: 700; }
div[data-testid="stSidebar"] { background: #1a237e; }
div[data-testid="stSidebar"] * { color: white !important; }
div[data-testid="stSidebar"] .stSelectbox label,
div[data-testid="stSidebar"] .stTextInput label { color: #b3c5ff !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 사이드바: 학원·학생 기본 정보
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏫 학원 정보")
    academy_name  = st.text_input("학원명",      value="클로드 수학학원")
    teacher_name  = st.text_input("담당 선생님",  value="김지훈 선생님")
    class_name    = st.text_input("반 이름",      value="초등 5학년 심화반")
    report_month  = st.selectbox("평가 월",       [f"{m}월" for m in range(1, 13)],
                                  index=datetime.now().month - 1)

    st.markdown("---")
    st.markdown("## 👤 학생 정보")
    student_name  = st.text_input("학생 이름",   value="홍길동")
    student_school = st.text_input("재학 학교",  value="서울초등학교")
    student_grade = st.selectbox("학년",         ["초등 3학년","초등 4학년","초등 5학년","초등 6학년",
                                                   "중학교 1학년","중학교 2학년","중학교 3학년"])

    st.markdown("---")
    st.markdown("## 🤖 AI 코멘트 설정")
    ai_mode = st.radio("코멘트 생성 방식",
                        ["📝 규칙 기반 (무료)", "🧠 Claude AI (유료·고품질)"],
                        index=0)
    if "Claude" in ai_mode:
        claude_key = st.text_input("Anthropic API Key", type="password",
                                    placeholder="sk-ant-...")
        st.caption("💳 Claude API: 성적표 1건당 약 $0.003~$0.008 (₩4~11원)")
    else:
        claude_key = ""

# ─────────────────────────────────────────────
# 메인 영역 – 탭 구성
# ─────────────────────────────────────────────
st.markdown(f"# 📊 학원 성적표 v2  <span style='font-size:16px;color:#888;font-weight:400'>{academy_name}</span>",
            unsafe_allow_html=True)

tab_input, tab_preview = st.tabs(["✏️ 성적 입력", "📋 성적표 미리보기 & 출력"])

# ═══════════════════════════════════════════
# TAB 1: 성적 입력
# ═══════════════════════════════════════════
with tab_input:
    col_left, col_right = st.columns([1, 1], gap="large")

    # ── 왼쪽: 점수 입력 ──
    with col_left:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("### 📝 이번 달 점수")

        student_score = st.number_input("학생 종합 점수 (점)", 0, 100, 85, 1)
        class_avg     = st.number_input("반 평균 점수 (점)",   0, 100, 76, 1)
        subject       = st.text_input("학습 단원/과목",        value="분수와 소수의 혼합 계산")

        st.markdown("#### 🎯 5대 평가 지표 (0~100)")
        m1 = st.slider("수업태도",       0, 100, 88)
        m2 = st.slider("과제수행",       0, 100, 82)
        m3 = st.slider("계산력(연산)",   0, 100, 90)
        m4 = st.slider("심화문제풀이",   0, 100, 72)
        m5 = st.slider("학업성취도",     0, 100, 85)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── 오른쪽: 성적 추이 ──
    with col_right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("### 📈 분기별 성적 추이 (선택 입력)")

        q_labels = ["1분기", "2분기", "3분기", "4분기(현재)"]
        q_scores = []
        for i, q in enumerate(q_labels):
            default = [70, 76, 80, student_score][i]
            val = st.number_input(q, 0, 100, default, 1, key=f"q{i}")
            q_scores.append(val)

        st.markdown("#### 📌 특이사항 메모")
        memo = st.text_area("담당 강사 메모 (선택)",
                             value="분수 나눗셈 역수 개념 정착 확인. 심화문제 3번 패턴 반복 오류 있음.",
                             height=120)
        st.markdown('</div>', unsafe_allow_html=True)

    # 분석 버튼
    st.markdown("---")
    gen_btn = st.button("🚀 성적표 생성하기", use_container_width=True, type="primary")

    if gen_btn:
        st.session_state["report_data"] = {
            "academy_name":   academy_name,
            "teacher_name":   teacher_name,
            "class_name":     class_name,
            "report_month":   report_month,
            "student_name":   student_name,
            "student_school": student_school,
            "student_grade":  student_grade,
            "student_score":  student_score,
            "class_avg":      class_avg,
            "subject":        subject,
            "metrics": {
                "수업태도":       m1,
                "과제수행":       m2,
                "계산력(연산)":   m3,
                "심화문제풀이":   m4,
                "학업성취도":     m5,
            },
            "q_scores":   q_scores,
            "q_labels":   q_labels,
            "memo":        memo,
            "ai_mode":     ai_mode,
            "claude_key":  claude_key,
        }
        st.success("✅ 데이터 저장 완료! '성적표 미리보기 & 출력' 탭을 클릭하세요.")

# ═══════════════════════════════════════════
# TAB 2: 미리보기
# ═══════════════════════════════════════════
with tab_preview:

    if "report_data" not in st.session_state:
        st.info("✏️ '성적 입력' 탭에서 데이터를 입력하고 '성적표 생성하기'를 눌러주세요.")
        st.stop()

    d = st.session_state["report_data"]

    # ─────────────────────────────────────────
    # AI / 규칙 기반 코멘트 생성
    # ─────────────────────────────────────────
    @st.cache_data(show_spinner=False)
    def rule_based_comment(d: dict) -> str:
        s   = d["student_score"]
        avg = d["class_avg"]
        m   = d["metrics"]
        diff = s - avg
        subj = d["subject"]
        grade = d["student_grade"]

        # 문단 1: 단원 연계성
        if "분수" in subj or "소수" in subj:
            p1 = (f"이번 달 학습 단원인 '{subj}'은(는) {grade} 수학 교육과정의 핵심 개념으로, "
                  f"분수와 소수 사이의 관계를 이해하고 사칙연산에 자유롭게 적용하는 능력을 기릅니다. "
                  f"해당 개념은 이후 중학교 1학년 유리수·정수 연산 및 방정식 단원의 직접적인 기초가 되며, "
                  f"연산의 정확도와 개념 이해 두 가지 모두 균형 있게 갖추는 것이 목표입니다.")
        elif "도형" in subj or "넓이" in subj or "부피" in subj:
            p1 = (f"이번 달 학습 단원인 '{subj}'은(는) 공간 감각과 수리 논리를 동시에 훈련하는 단원입니다. "
                  f"초등 과정의 도형 학습은 중학교 기하 단원(합동·닮음·피타고라스 정리)의 초석이 되므로 "
                  f"공식 암기에 그치지 않고 원리를 이해하는 방향으로 지도하고 있습니다.")
        else:
            p1 = (f"이번 달 학습 단원인 '{subj}'은(는) {grade} 수학 교육과정의 주요 학습 주제로, "
                  f"논리적 사고력과 계산 정확도를 함께 요구합니다. "
                  f"해당 내용은 이후 상급 학년 과정의 기초 개념으로 연결되므로 "
                  f"단순 풀이 암기보다 원리 이해 중심의 학습이 중요합니다.")

        # 문단 2: 정밀 관찰
        weak_metrics  = [k for k, v in m.items() if v < 75]
        strong_metrics = [k for k, v in m.items() if v >= 90]

        obs_parts = []
        if diff >= 10:
            obs_parts.append(f"이번 달 {d['student_name']} 학생은 반 평균 대비 {diff:+d}점을 기록하며 우수한 성취를 보였습니다.")
        elif diff >= 0:
            obs_parts.append(f"이번 달 종합 점수는 반 평균보다 {diff:+d}점으로, 평균 수준의 학습 성취를 유지하고 있습니다.")
        else:
            obs_parts.append(f"이번 달 종합 점수가 반 평균보다 {diff}점 낮게 나타났습니다. 아래 사항에 집중적인 보완이 필요합니다.")

        if strong_metrics:
            obs_parts.append(f"특히 {', '.join(strong_metrics)} 영역에서 90점 이상의 높은 역량을 보였습니다.")
        if weak_metrics:
            obs_parts.append(f"반면 {', '.join(weak_metrics)} 영역은 75점 미만으로, 보완이 필요한 부분입니다.")
        if d["memo"]:
            obs_parts.append(f"수업 중 관찰 사항: {d['memo']}")

        p2 = " ".join(obs_parts)

        # 문단 3: 로드맵
        trend = d["q_scores"]
        if len(trend) >= 2 and trend[-1] > trend[-2]:
            trend_msg = f"지난 분기 대비 {trend[-1] - trend[-2]:+d}점 향상된 긍정적인 흐름을 이어가고 있습니다."
        elif len(trend) >= 2 and trend[-1] < trend[-2]:
            trend_msg = f"지난 분기 대비 {trend[-1] - trend[-2]}점 하락하였으나, 개념 보완을 통해 충분히 회복 가능합니다."
        else:
            trend_msg = "꾸준한 학습 흐름을 유지하고 있습니다."

        p3 = (f"{trend_msg} 다음 달 과정에서는 {subj}의 응용 문제 풀이 확장 및 "
              f"이전 단원 연계 복습을 병행할 예정입니다. "
              f"꾸준한 가정 내 학습 루틴을 함께 유지해 주시면 더욱 좋은 결과를 기대할 수 있습니다.")

        return f"{p1}\n\n{p2}\n\n{p3}"

    def claude_ai_comment(d: dict, api_key: str) -> str:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            metrics_str = "\n".join([f"  - {k}: {v}점" for k, v in d["metrics"].items()])
            prompt = f"""당신은 수학 전문 학원의 담당 강사입니다. 다음 데이터를 바탕으로 학부모 상담용 성적 진단 리포트를 작성하십시오.

[학생 정보]
- 이름: {d['student_name']} ({d['student_grade']})
- 학습 단원: {d['subject']}
- 이번 달 점수: {d['student_score']}점 (반 평균: {d['class_avg']}점)
- 5대 평가 지표:
{metrics_str}
- 분기별 성적: {dict(zip(d['q_labels'], d['q_scores']))}
- 강사 메모: {d['memo']}

[작성 규칙]
- 과도한 미사여구 없이 사실 기반 담백한 교육 컨설턴트 톤
- 반드시 아래 3문단 구조 준수:

1문단(단원 연계성): 이번 달 학습 단원의 핵심 개념 + 중/고등 과정 기초 역할 (4~5줄)
2문단(정밀 관찰): 점수·지표 데이터 기반의 학생 학습 습관, 강점, 보완점 명시 (4~5줄)
3문단(로드맵): 다음 달 진도 계획 + 가정 연계 학습 제안 (3~4줄)

JSON이나 코드 없이 순수 텍스트 3문단만 출력하십시오."""

            msg = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=700,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text
        except Exception as e:
            return f"[Claude AI 오류: {e}]\n\n" + rule_based_comment(d)

    # 코멘트 생성
    with st.spinner("코멘트 생성 중..."):
        if "Claude" in d["ai_mode"] and d["claude_key"]:
            comment_text = claude_ai_comment(d, d["claude_key"])
        else:
            comment_text = rule_based_comment(d)

    # ─────────────────────────────────────────
    # 차트 생성 함수들
    # ─────────────────────────────────────────
    BLUE   = "#1a237e"
    BLUE2  = "#3949ab"
    SILVER = "#90a4ae"
    ORANGE = "#e65100"
    GOLD   = "#f9a825"

    def make_bar_chart(d: dict) -> go.Figure:
        s   = d["student_score"]
        avg = d["class_avg"]
        diff = s - avg
        bar_color = BLUE2 if diff >= 0 else "#c62828"

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name=d["student_name"],
            x=["종합 점수"],
            y=[s],
            marker=dict(color=bar_color, line=dict(width=0)),
            text=[f"<b>{s}점</b>"],
            textposition="outside",
            textfont=dict(size=18, color=bar_color),
            width=0.28,
        ))
        fig.add_trace(go.Bar(
            name="반 평균",
            x=["종합 점수"],
            y=[avg],
            marker=dict(color=SILVER, line=dict(width=0)),
            text=[f"<b>{avg}점</b>"],
            textposition="outside",
            textfont=dict(size=18, color="#555"),
            width=0.28,
        ))
        # 편차 주석
        sign = "+" if diff >= 0 else ""
        fig.add_annotation(
            x=0.5, y=max(s, avg) + 8,
            xref="paper", yref="y",
            text=f"편차 {sign}{diff}점",
            showarrow=False,
            font=dict(size=14, color=bar_color, family="Noto Sans KR"),
            bgcolor="white",
            bordercolor=bar_color,
            borderwidth=1,
            borderpad=5,
        )
        fig.update_layout(
            barmode="group",
            height=360,
            margin=dict(l=10, r=10, t=20, b=10),
            paper_bgcolor="white",
            plot_bgcolor="white",
            yaxis=dict(range=[0, 115], showgrid=True, gridcolor="#f0f0f0",
                       ticksuffix="점", tickfont=dict(size=12)),
            xaxis=dict(showticklabels=False),
            legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center",
                        font=dict(size=13)),
            font=dict(family="Noto Sans KR"),
        )
        return fig

    def make_radar_chart(d: dict) -> go.Figure:
        cats   = list(d["metrics"].keys())
        vals   = list(d["metrics"].values())
        cats_r = cats + [cats[0]]
        vals_r = vals + [vals[0]]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=[100] * (len(cats) + 1),
            theta=cats_r,
            fill="toself",
            fillcolor="rgba(236,239,241,0.6)",
            line=dict(color="#cfd8dc", width=1),
            name="만점 기준",
            showlegend=False,
        ))
        fig.add_trace(go.Scatterpolar(
            r=vals_r,
            theta=cats_r,
            fill="toself",
            fillcolor="rgba(57,73,171,0.18)",
            line=dict(color=BLUE2, width=2.5),
            marker=dict(size=9, color=BLUE2, line=dict(width=2, color="white")),
            name=d["student_name"],
        ))
        fig.update_layout(
            polar=dict(
                bgcolor="white",
                radialaxis=dict(
                    visible=True, range=[0, 100],
                    tickvals=[25, 50, 75, 100],
                    ticktext=["25", "50", "75", "100"],
                    tickfont=dict(size=10, color="#999"),
                    gridcolor="#e0e0e0",
                    linecolor="#e0e0e0",
                ),
                angularaxis=dict(
                    tickfont=dict(size=13, color="#333", family="Noto Sans KR"),
                    linecolor="#ccc",
                ),
            ),
            height=340,
            margin=dict(l=50, r=50, t=30, b=30),
            paper_bgcolor="white",
            showlegend=False,
            font=dict(family="Noto Sans KR"),
        )
        return fig

    def make_trend_chart(d: dict) -> go.Figure:
        labels = d["q_labels"]
        scores = d["q_scores"]
        avg_line = [d["class_avg"]] * len(labels)

        fig = go.Figure()
        # 반 평균 점선
        fig.add_trace(go.Scatter(
            x=labels, y=avg_line,
            mode="lines",
            line=dict(color=SILVER, width=1.5, dash="dot"),
            name="반 평균",
        ))
        # 학생 추이
        fig.add_trace(go.Scatter(
            x=labels, y=scores,
            mode="lines+markers+text",
            line=dict(color=ORANGE, width=3),
            marker=dict(size=11, color=ORANGE,
                        line=dict(width=2, color="white")),
            text=[f"<b>{s}점</b>" for s in scores],
            textposition="top center",
            textfont=dict(size=13, color=ORANGE),
            name=d["student_name"],
            fill="tozeroy",
            fillcolor="rgba(230,81,0,0.07)",
        ))
        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=20, b=10),
            paper_bgcolor="white",
            plot_bgcolor="white",
            yaxis=dict(range=[max(0, min(scores) - 15), 108],
                       showgrid=True, gridcolor="#f5f5f5",
                       ticksuffix="점", tickfont=dict(size=12)),
            xaxis=dict(tickfont=dict(size=13, family="Noto Sans KR")),
            legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center",
                        font=dict(size=12)),
            font=dict(family="Noto Sans KR"),
        )
        return fig

    # ─────────────────────────────────────────
    # Streamlit 미리보기
    # ─────────────────────────────────────────
    st.markdown(f"""
<div style="background:linear-gradient(135deg,{BLUE},{BLUE2});
            color:white;border-radius:14px;padding:28px 32px;margin-bottom:20px;">
  <div style="font-size:13px;opacity:.75;letter-spacing:2px;margin-bottom:4px;">
    {d['academy_name']} · {d['class_name']} · {d['report_month']} 성적표
  </div>
  <div style="font-size:30px;font-weight:900;letter-spacing:-1px;">
    {d['student_name']} 학생 월간 학업 성취 리포트
  </div>
  <div style="margin-top:8px;font-size:14px;opacity:.8;">
    {d['student_school']} | {d['student_grade']} | 담당: {d['teacher_name']}
  </div>
</div>
""", unsafe_allow_html=True)

    # 요약 지표 3개
    diff = d["student_score"] - d["class_avg"]
    sign = "+" if diff >= 0 else ""
    pill_cls = "pill-blue" if diff >= 0 else "pill-red"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="section-card" style="text-align:center;">
            <div style="font-size:13px;color:#888;margin-bottom:6px;">학생 종합 점수</div>
            <div style="font-size:44px;font-weight:900;color:{BLUE2};">{d['student_score']}점</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="section-card" style="text-align:center;">
            <div style="font-size:13px;color:#888;margin-bottom:6px;">반 평균 점수</div>
            <div style="font-size:44px;font-weight:900;color:#546e7a;">{d['class_avg']}점</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        clr = BLUE2 if diff >= 0 else "#c62828"
        st.markdown(f"""<div class="section-card" style="text-align:center;">
            <div style="font-size:13px;color:#888;margin-bottom:6px;">성취도 편차</div>
            <div style="font-size:44px;font-weight:900;color:{clr};">{sign}{diff}점</div>
        </div>""", unsafe_allow_html=True)

    # 차트 행 1: 막대 + 레이더
    c_bar, c_radar = st.columns(2, gap="large")
    with c_bar:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 📊 종합 점수 비교")
        st.plotly_chart(make_bar_chart(d), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)
    with c_radar:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 🕸️ 5대 영역별 역량 분포")
        st.plotly_chart(make_radar_chart(d), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    # 차트 행 2: 성적 추이
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### 📈 분기별 성적 향상 추이")
    st.plotly_chart(make_trend_chart(d), use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

    # 5대 지표 뱃지
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### 🏷️ 5대 평가 지표 점수")
    badge_html = ""
    for label, val in d["metrics"].items():
        if val >= 90:
            cls = "pill-blue"
        elif val >= 75:
            cls = "pill-green"
        elif val >= 60:
            cls = "pill-orange"
        else:
            cls = "pill-red"
        badge_html += f'<span class="metric-pill {cls}">{label} {val}점</span>'
    st.markdown(badge_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 전문가 코멘트
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    mode_label = "Claude AI 생성" if "Claude" in d["ai_mode"] and d["claude_key"] else "규칙 기반 생성"
    st.markdown(f"#### 📝 교육 전문가 심층 진단  <span style='font-size:12px;color:#aaa;'>{mode_label}</span>",
                unsafe_allow_html=True)
    for para in comment_text.split("\n\n"):
        if para.strip():
            st.markdown(f"> {para.strip()}")
    st.markdown('</div>', unsafe_allow_html=True)

    # ─────────────────────────────────────────
    # HTML 리포트 생성 (인쇄용)
    # ─────────────────────────────────────────
    def build_print_html(d: dict, comment: str) -> str:
        bar_html   = make_bar_chart(d).to_html(full_html=False, include_plotlyjs="cdn",
                                                config={"displayModeBar": False})
        radar_html = make_radar_chart(d).to_html(full_html=False, include_plotlyjs=False,
                                                  config={"displayModeBar": False})
        trend_html = make_trend_chart(d).to_html(full_html=False, include_plotlyjs=False,
                                                  config={"displayModeBar": False})

        diff = d["student_score"] - d["class_avg"]
        sign = "+" if diff >= 0 else ""
        diff_color = "#1a237e" if diff >= 0 else "#c62828"

        metrics_rows = ""
        for label, val in d["metrics"].items():
            filled = int(val / 100 * 20)
            bar = "█" * filled + "░" * (20 - filled)
            grade = "우수" if val >= 90 else "양호" if val >= 75 else "보통" if val >= 60 else "미흡"
            grade_color = "#1565c0" if val >= 90 else "#2e7d32" if val >= 75 else "#e65100" if val >= 60 else "#c62828"
            metrics_rows += f"""
            <tr>
              <td style="padding:9px 14px;font-weight:600;color:#333;width:130px;">{label}</td>
              <td style="padding:9px 14px;font-size:11px;color:#888;letter-spacing:-0.5px;">{bar}</td>
              <td style="padding:9px 14px;font-weight:700;color:#1a237e;text-align:right;width:55px;">{val}점</td>
              <td style="padding:9px 14px;text-align:right;width:50px;">
                <span style="background:{grade_color}22;color:{grade_color};padding:2px 8px;
                             border-radius:10px;font-size:11px;font-weight:700;">{grade}</span>
              </td>
            </tr>"""

        paras_html = "".join(
            f"<p style='margin:0 0 18px 0;text-indent:1em;'>{p.strip()}</p>"
            for p in comment.split("\n\n") if p.strip()
        )
        trend_labels = ", ".join([f"{l}: {s}점" for l, s in zip(d["q_labels"], d["q_scores"])])

        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Noto Sans KR', sans-serif;
    background: #eceff1;
    padding: 20px;
  }}
  @media print {{
    body {{ background: white !important; padding: 0; }}
    .no-print {{ display: none !important; }}
    @page {{ size: A4 portrait; margin: 0; }}
    .page {{ box-shadow: none !important; margin: 0 !important; }}
  }}

  /* ── A4 페이지 ── */
  .page {{
    width: 210mm;
    min-height: 296mm;
    background: white;
    margin: 0 auto 20px auto;
    padding: 14mm 18mm;
    box-shadow: 0 4px 20px rgba(0,0,0,0.12);
    page-break-after: always;
    position: relative;
  }}
  .page:last-child {{ page-break-after: auto; }}

  /* ── 헤더 ── */
  .page-header {{
    background: linear-gradient(135deg, #1a237e, #3949ab);
    color: white;
    border-radius: 10px;
    padding: 18px 24px;
    margin-bottom: 22px;
  }}
  .page-header .academy {{ font-size: 11pt; opacity: .75; letter-spacing: 1px; margin-bottom: 4px; }}
  .page-header .title   {{ font-size: 20pt; font-weight: 900; letter-spacing: -0.5px; }}
  .page-header .sub     {{ font-size: 10pt; opacity: .8; margin-top: 5px; }}

  /* ── 섹션 제목 ── */
  .sec-title {{
    font-size: 13pt; font-weight: 800; color: #1a237e;
    border-left: 5px solid #3949ab; padding-left: 10px;
    margin: 20px 0 12px 0;
  }}

  /* ── 요약 박스 3개 ── */
  .score-row {{ display: flex; gap: 12px; margin-bottom: 18px; }}
  .score-box {{
    flex: 1; text-align: center; border-radius: 10px;
    padding: 14px 10px; border: 1.5px solid #e0e0e0;
  }}
  .score-box .lbl {{ font-size: 9pt; color: #888; margin-bottom: 5px; }}
  .score-box .val {{ font-size: 26pt; font-weight: 900; }}

  /* ── 지표 테이블 ── */
  .metrics-table {{
    width: 100%; border-collapse: collapse;
    background: #fafafa; border-radius: 8px; overflow: hidden;
    border: 1px solid #eeeeee;
  }}
  .metrics-table tr {{ border-bottom: 1px solid #eeeeee; }}
  .metrics-table tr:last-child {{ border-bottom: none; }}
  .metrics-table tr:nth-child(even) {{ background: #f5f7ff; }}

  /* ── 코멘트 ── */
  .comment-box {{
    font-size: 11pt; line-height: 2.0; color: #424242;
    border-top: 4px solid #1a237e;
    padding-top: 16px;
  }}

  /* ── 푸터 ── */
  .page-footer {{
    position: absolute; bottom: 12mm; left: 18mm; right: 18mm;
    display: flex; justify-content: space-between; align-items: center;
    border-top: 1px solid #e0e0e0; padding-top: 8px;
    font-size: 9pt; color: #aaa;
  }}

  /* ── 인쇄 버튼 ── */
  .print-btn {{
    display: block; width: 300px; margin: 0 auto 20px auto;
    background: #1a237e; color: white; border: none;
    padding: 16px 32px; border-radius: 12px;
    font-size: 16px; font-weight: 700; cursor: pointer;
    font-family: 'Noto Sans KR', sans-serif;
  }}
  .print-btn:hover {{ background: #3949ab; }}
</style>
</head>
<body>

<button class="print-btn no-print" onclick="window.print()">🖨️ A4 인쇄 / PDF 저장</button>

<!-- ═══════════════ PAGE 1 ═══════════════ -->
<div class="page">
  <div class="page-header">
    <div class="academy">{d['academy_name']} · {d['class_name']} · {d['report_month']} 월간 성적표</div>
    <div class="title">{d['student_name']} 학생 학업 성취 리포트</div>
    <div class="sub">{d['student_school']} | {d['student_grade']} | 담당: {d['teacher_name']}</div>
  </div>

  <div class="score-row">
    <div class="score-box">
      <div class="lbl">학생 종합 점수</div>
      <div class="val" style="color:#1a237e;">{d['student_score']}점</div>
    </div>
    <div class="score-box">
      <div class="lbl">해당 과정 평균</div>
      <div class="val" style="color:#546e7a;">{d['class_avg']}점</div>
    </div>
    <div class="score-box">
      <div class="lbl">성취도 편차</div>
      <div class="val" style="color:{diff_color};">{sign}{diff}점</div>
    </div>
  </div>

  <div class="sec-title">📊 종합 점수 비교 (학생 vs 반 평균)</div>
  <div style="height:360px;">{bar_html}</div>

  <div class="sec-title" style="margin-top:16px;">🏷️ 5대 평가 지표 상세</div>
  <table class="metrics-table">{metrics_rows}</table>

  <div class="page-footer">
    <span>{d['academy_name']}</span>
    <span>발행일: {datetime.now().strftime('%Y년 %m월 %d일')} · 1 / 2</span>
  </div>
</div>

<!-- ═══════════════ PAGE 2 ═══════════════ -->
<div class="page">
  <div class="page-header">
    <div class="academy">{d['academy_name']} · 심층 분석</div>
    <div class="title">{d['student_name']} 학생 — 역량 분석 & 성장 추이</div>
    <div class="sub">학습 단원: {d['subject']}</div>
  </div>

  <div style="display:flex;gap:20px;">
    <div style="flex:1;">
      <div class="sec-title">🕸️ 영역별 역량 분포</div>
      <div style="height:310px;">{radar_html}</div>
    </div>
    <div style="flex:1;">
      <div class="sec-title">📈 분기별 성적 추이</div>
      <div style="height:310px;">{trend_html}</div>
      <p style="font-size:9pt;color:#999;margin-top:6px;text-align:center;">{trend_labels}</p>
    </div>
  </div>

  <div class="sec-title" style="margin-top:20px;">📝 교육 전문가 심층 진단</div>
  <div class="comment-box">{paras_html}</div>

  <div class="page-footer">
    <span>{d['teacher_name']} 작성</span>
    <span>발행일: {datetime.now().strftime('%Y년 %m월 %d일')} · 2 / 2</span>
  </div>
</div>

</body>
</html>"""

    # ─────────────────────────────────────────
    # 다운로드 버튼
    # ─────────────────────────────────────────
    st.markdown("---")
    html_report = build_print_html(d, comment_text)
    b64 = base64.b64encode(html_report.encode("utf-8")).decode()
    filename = f"성적표_{d['student_name']}_{d['report_month']}_{datetime.now().strftime('%m%d')}.html"

    col_dl, col_info = st.columns([2, 3])
    with col_dl:
        st.markdown(
            f'<a href="data:text/html;base64,{b64}" download="{filename}" '
            f'style="display:block;background:#1a237e;color:white;text-align:center;'
            f'padding:16px;border-radius:12px;font-size:16px;font-weight:700;'
            f'text-decoration:none;margin-top:4px;">'
            f'⬇️ HTML 성적표 다운로드</a>',
            unsafe_allow_html=True,
        )
    with col_info:
        st.info("💡 다운로드한 HTML 파일을 브라우저에서 열고 **Ctrl+P (Mac: ⌘+P)** → '대상: PDF로 저장' 또는 직접 인쇄하세요. 완벽한 A4 2페이지로 출력됩니다.")
