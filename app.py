import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import base64, io

# ═══════════════════════════════════════════════════════
# 색상 팔레트 (프리미엄 네이비·골드 테마)
# ═══════════════════════════════════════════════════════
NAVY  = "#0B1F4B"
NAVY2 = "#1E3A6E"
GOLD  = "#C9A84C"
GOLD2 = "#F0DFA0"
SILVER= "#8A9BB0"
CREAM = "#FAF9F6"
GREEN = "#1B6B3A"
ORANGE= "#C85000"
RED   = "#A31515"

def grade_info(score):
    """등급 (표시명, 색상) — 부정적 표현 완전 제거"""
    if score >= 95: return "최우수", GOLD
    if score >= 90: return "우수",   "#1A5276"
    if score >= 85: return "우수",   "#1A5276"
    if score >= 80: return "양호",   "#1B6B3A"
    if score >= 75: return "양호",   "#1B6B3A"
    return "성장중", "#5D7A8C"  # 낮은 점수도 긍정적 표현

# ═══════════════════════════════════════════════════════
# 페이지 설정 & 전역 CSS
# ═══════════════════════════════════════════════════════
st.set_page_config(page_title="학원 성적표 v2", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
html, body, [class*="css"] {{ font-family:'Noto Sans KR',sans-serif; }}
.stApp {{ background:#EEF1F7; }}
.stButton>button {{ border-radius:10px; font-weight:700; font-size:15px; }}
div[data-testid="stSidebar"] {{ background:{NAVY}; }}
div[data-testid="stSidebar"] * {{ color:white !important; }}
div[data-testid="stSidebar"] .stRadio label {{ color:{GOLD2} !important; }}
/* 입력 섹션 카드 */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius:14px;
    box-shadow:0 2px 14px rgba(11,31,75,0.09);
}}
/* 메트릭 뱃지 */
.badge {{
    display:inline-block; padding:5px 14px;
    border-radius:20px; font-size:12px; font-weight:700; margin:3px;
}}
.b-gold   {{ background:{GOLD}22; color:{GOLD};   border:1px solid {GOLD}55; }}
.b-blue   {{ background:#1A527622; color:#1A5276; border:1px solid #1A527655; }}
.b-green  {{ background:{GREEN}22; color:{GREEN};  border:1px solid {GREEN}55; }}
.b-orange {{ background:{ORANGE}22;color:{ORANGE}; border:1px solid {ORANGE}55; }}
.b-red    {{ background:{RED}22;  color:{RED};    border:1px solid {RED}55; }}
</style>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# 사이드바
# ═══════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"<div style='color:{GOLD};font-size:18px;font-weight:900;margin-bottom:4px'>🏫 학원 정보</div>",
                unsafe_allow_html=True)
    academy_name   = st.text_input("학원명",      value="클로드 수학학원")
    teacher_name   = st.text_input("담당 선생님",  value="김지훈 선생님")
    class_name     = st.text_input("반 이름",      value="초등 5학년 심화반")
    report_month   = st.selectbox("평가 월", [f"{m}월" for m in range(1,13)],
                                   index=datetime.now().month-1)
    st.markdown("---")
    st.markdown(f"<div style='color:{GOLD};font-size:18px;font-weight:900;margin-bottom:4px'>👤 학생 정보</div>",
                unsafe_allow_html=True)
    student_name   = st.text_input("학생 이름",   value="홍길동")
    student_school = st.text_input("재학 학교",   value="서울초등학교")
    student_grade  = st.selectbox("학년", ["초등 3학년","초등 4학년","초등 5학년","초등 6학년",
                                           "중학교 1학년","중학교 2학년","중학교 3학년"])
    st.markdown("---")
    st.markdown(f"<div style='color:{GOLD};font-size:18px;font-weight:900;margin-bottom:4px'>🤖 AI 설정</div>",
                unsafe_allow_html=True)
    ai_mode = st.radio("코멘트 생성 방식",
                        ["📝 규칙 기반 (무료)","🧠 Claude AI (유료·고품질)"],index=0)
    claude_key = ""
    if "Claude" in ai_mode:
        claude_key = st.text_input("Anthropic API Key", type="password",
                                    placeholder="sk-ant-...")
        st.caption("💳 텍스트만: ₩4~11원 | 이미지 분석 포함: ₩15~30원/건")

# ═══════════════════════════════════════════════════════
# 헤더
# ═══════════════════════════════════════════════════════
st.markdown(f"""
<div style="background:linear-gradient(135deg,{NAVY},{NAVY2});border-radius:16px;
     padding:20px 28px;margin-bottom:20px;
     border-bottom:4px solid {GOLD};">
  <span style="font-size:26px;font-weight:900;color:white;font-family:'Noto Serif KR'">
    📊 학원 성적표 v2
  </span>
  <span style="font-size:14px;color:{GOLD2};margin-left:14px">{academy_name}</span>
</div>""", unsafe_allow_html=True)

tab_input, tab_preview = st.tabs(["✏️ 성적 입력", "📋 성적표 미리보기 & 출력"])

# ═══════════════════════════════════════════════════════
# TAB 1: 성적 입력
# ═══════════════════════════════════════════════════════
with tab_input:

    # ── 시험지 업로드 ───────────────────────────
    with st.container(border=True):
        st.markdown(f"### 📎 시험지 업로드 <span style='font-size:13px;color:{GOLD};'>(Claude AI 모드에서 문항별 분석 자동 반영)</span>",
                    unsafe_allow_html=True)
        st.caption("JPG · PNG · PDF 지원 | 여러 장 동시 업로드 가능 | 파일 없이 수동 입력만으로도 생성 가능")
        uploaded_files = st.file_uploader("파일 선택",
            type=["jpg","jpeg","png","pdf"], accept_multiple_files=True,
            label_visibility="collapsed")
        if uploaded_files:
            cols = st.columns(min(len(uploaded_files),5))
            for i,f in enumerate(uploaded_files):
                if f.type.startswith("image"):
                    cols[i%5].image(f, caption=f.name, use_container_width=True)
                else:
                    cols[i%5].markdown(f"📄 `{f.name}`")
            st.success(f"✅ {len(uploaded_files)}개 파일 업로드 완료")

    st.markdown("")
    col_L, col_R = st.columns(2, gap="large")

    with col_L:
        with st.container(border=True):
            st.markdown("### 📝 이번 달 점수")
            # ── [FIX 2] 소수점 지원 ─────────────
            student_score = st.number_input("학생 종합 점수", 0.0, 100.0, 85.0, 0.5,
                                             format="%.1f",
                                             help="소수점 입력 가능 (예: 62.5)")
            class_avg     = st.number_input("반 평균 점수",   0.0, 100.0, 76.0, 0.5,
                                             format="%.1f")
            subject       = st.text_input("학습 단원/과목", value="분수와 소수의 혼합 계산")
            st.markdown(f"#### 🎯 5대 평가 지표")
            m1 = st.slider("① 수업태도",       0, 100, 88)
            m2 = st.slider("② 과제수행",       0, 100, 82)
            m3 = st.slider("③ 계산력(연산)",   0, 100, 90)
            m4 = st.slider("④ 심화문제풀이",   0, 100, 72)
            m5 = st.slider("⑤ 학업성취도",     0, 100, 85)

    with col_R:
        with st.container(border=True):
            st.markdown("### 📈 분기별 성적 추이")
            q_labels = ["1분기","2분기","3분기","4분기(현재)"]
            q_scores = []
            for i,q in enumerate(q_labels):
                dft = [70,76,80,int(student_score)][i]
                val = st.number_input(q, 0.0, 100.0, float(dft), 0.5,
                                      format="%.1f", key=f"q{i}")
                q_scores.append(val)
            st.markdown("#### 📌 강사 관찰 메모")
            memo = st.text_area("",
                value="분수 나눗셈 역수 개념 정착 확인. 심화문제 3번 패턴 반복 오류 있음.",
                height=150, label_visibility="collapsed")

    st.markdown("")
    gen_btn = st.button("🚀 성적표 생성하기", use_container_width=True, type="primary")

    if gen_btn:
        files_data = []
        for f in (uploaded_files or []):
            files_data.append({"name":f.name,"type":f.type,"bytes":f.getvalue()})

        # ── [FIX 1] 시험지 문항 분석 (Claude AI + 이미지 있을 때) ──
        exam_analysis = None
        if "Claude" in ai_mode and claude_key and files_data:
            img_files = [fd for fd in files_data if "image" in fd["type"]]
            if img_files:
                with st.spinner("📖 시험지 문항별 분석 중 (Claude Vision)..."):
                    try:
                        import anthropic
                        client = anthropic.Anthropic(api_key=claude_key)
                        content = []
                        for fd in img_files:
                            b64 = base64.b64encode(fd["bytes"]).decode()
                            content.append({"type":"image",
                                "source":{"type":"base64","media_type":fd["type"],"data":b64}})
                        content.append({"type":"text","text":"""이 수학 시험지를 꼼꼼히 분석하세요.

아래 항목을 **한국어**로 정확하게 파악하여 서술하세요:

1. **맞은 문항**: 정답 표시(O, ✓, 빨간 동그라미 없음)가 있는 문항 번호
2. **틀린 문항**: 오답 표시(X, 빨간 줄, 감점 표시)가 있는 문항 번호
3. **오답 패턴 분석**: 틀린 문제들의 공통 유형 (예: 분수 통분 오류, 부호 실수, 단위 혼동, 개념 혼동 등)
4. **강점 유형**: 맞은 문제들의 공통 특징 (어떤 유형 문제에 강한지)
5. **풀이 습관**: 풀이 과정 기재 여부, 검산 흔적, 지우개 사용 패턴, 글씨 정돈 상태 등

시험지가 불명확하거나 채점 표시가 없으면 "이미지에서 채점 정보를 확인하기 어렵습니다"라고 명시하세요."""})
                        msg = client.messages.create(
                            model="claude-opus-4-6", max_tokens=600,
                            messages=[{"role":"user","content":content}])
                        exam_analysis = msg.content[0].text
                        st.success("✅ 시험지 분석 완료")
                    except Exception as e:
                        exam_analysis = None
                        st.warning(f"시험지 분석 실패: {e}")

        st.session_state["report_data"] = dict(
            academy_name=academy_name, teacher_name=teacher_name,
            class_name=class_name,    report_month=report_month,
            student_name=student_name, student_school=student_school,
            student_grade=student_grade,
            student_score=float(student_score), class_avg=float(class_avg),
            subject=subject,
            metrics={"수업태도":m1,"과제수행":m2,"계산력(연산)":m3,
                     "심화문제풀이":m4,"학업성취도":m5},
            q_scores=[float(s) for s in q_scores], q_labels=q_labels,
            memo=memo, ai_mode=ai_mode, claude_key=claude_key,
            files_data=files_data, exam_analysis=exam_analysis,
        )
        st.success("✅ 완료! '📋 성적표 미리보기 & 출력' 탭을 클릭하세요.")

# ═══════════════════════════════════════════════════════
# TAB 2: 미리보기
# ═══════════════════════════════════════════════════════
with tab_preview:
    if "report_data" not in st.session_state:
        st.info("✏️ '성적 입력' 탭에서 데이터를 입력하고 '성적표 생성하기'를 눌러주세요.")
        st.stop()

    d = st.session_state["report_data"]

    # ── 코멘트 생성 ───────────────────────────────
    def rule_based_comment(d):
        s,avg = d["student_score"],d["class_avg"]
        m,diff = d["metrics"],s-avg
        subj,grade = d["subject"],d["student_grade"]

        if "분수" in subj or "소수" in subj:
            p1=(f"이번 달 학습 단원 '{subj}'은(는) {grade} 수학의 핵심 개념으로, "
                f"분수·소수 간 변환과 사칙연산 응용 능력을 동시에 요구합니다. "
                f"이 단원은 중학교 1학년 유리수·방정식, 나아가 고교 수학의 수 체계 전반의 "
                f"직접적인 기초가 되므로, 단순 계산 능숙도뿐 아니라 '왜 그렇게 되는가'의 "
                f"원리 이해까지 함께 체화하는 것이 장기적으로 중요합니다.")
        elif "도형" in subj or "넓이" in subj or "부피" in subj:
            p1=(f"이번 달 학습 단원 '{subj}'은(는) 공간 감각과 논리적 추론 능력을 "
                f"동시에 훈련하는 단원입니다. 초등 도형 학습은 중학교 기하(합동·닮음·피타고라스 정리) "
                f"및 고교 도형과 방정식 단원의 초석이 되므로, 공식 암기에 그치지 않고 "
                f"도형의 성질과 원리를 시각적으로 이해하는 방향으로 지도하고 있습니다.")
        else:
            p1=(f"이번 달 학습 단원 '{subj}'은(는) {grade} 수학 과정의 주요 주제로 "
                f"논리적 사고력과 연산 정확도를 함께 요구합니다. "
                f"이후 상급 학년 과정의 기초 개념으로 직접 연결되는 내용인 만큼, "
                f"풀이 과정을 단계적으로 서술하는 습관을 함께 기르도록 지도하고 있습니다.")

        weak   = [k for k,v in m.items() if v<75]
        strong = [k for k,v in m.items() if v>=90]
        obs=[]
        if diff>=10:
            obs.append(f"{d['student_name']} 학생은 이번 달 반 평균 대비 {diff:+.1f}점으로 우수한 성취를 기록했습니다.")
        elif diff>=0:
            obs.append(f"종합 점수는 반 평균 대비 {diff:+.1f}점으로 안정적인 학습 성취를 유지하고 있습니다.")
        else:
            obs.append(f"종합 점수가 반 평균보다 {diff:.1f}점 낮아 집중 보완이 필요한 상황입니다.")
        if strong:
            obs.append(f"5대 지표 중 {', '.join(strong)} 영역에서 90점 이상의 뛰어난 역량을 보이고 있습니다.")
        if weak:
            obs.append(f"반면 {', '.join(weak)} 영역(75점 미만)은 보완이 필요하며, 수업 중 관련 유형의 반복 훈련을 강화하고 있습니다.")
        if d["memo"]:
            obs.append(f"수업 중 관찰 내용: {d['memo']}")
        p2=" ".join(obs)

        qs=d["q_scores"]
        if qs[-1]>qs[-2]: tmsg=f"지난 분기 대비 {qs[-1]-qs[-2]:+.1f}점 향상된 긍정적인 흐름입니다."
        elif qs[-1]<qs[-2]: tmsg=f"지난 분기 대비 {qs[-1]-qs[-2]:.1f}점 하락하였으나, 개념 보완으로 충분히 회복 가능합니다."
        else: tmsg="꾸준한 학습 흐름을 유지하고 있습니다."
        p3=(f"{tmsg} 다음 달에는 '{subj}' 단원 응용 심화 문제 풀이 확장과 "
            f"이전 단원 연계 복습을 병행할 예정입니다. "
            f"정기적인 오답 노트 정리와 가정 내 15~20분 복습 루틴을 함께 유지해 주시면 "
            f"더욱 안정적인 성적 향상을 기대할 수 있습니다.")

        # ── 시험지 분석 결과가 있으면 2문단에 통합 ──
        if d.get("exam_analysis"):
            exam_txt = d["exam_analysis"]
            p2 = (p2 + f"\n\n업로드된 시험지를 문항별로 분석한 결과: {exam_txt}")

        return f"{p1}\n\n{p2}\n\n{p3}"

    def claude_ai_comment(d):
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=d["claude_key"])
            metrics_str="\n".join(f"  - {k}: {v}점" for k,v in d["metrics"].items())
            exam_section = ""
            if d.get("exam_analysis"):
                exam_section = f"""
[시험지 문항별 분석 결과 — 반드시 2문단에 구체적으로 반영할 것]
{d['exam_analysis']}
"""
            content=[{"type":"text","text":f"""당신은 10년 경력의 대치동 수학 전문 학원 강사입니다.
아래 데이터와 시험지 분석 결과를 종합하여 학부모 상담용 성적 진단 리포트를 작성하십시오.

[학생 데이터]
- 이름: {d['student_name']} ({d['student_grade']})
- 학습 단원: {d['subject']}
- 종합 점수: {d['student_score']}점 (반 평균: {d['class_avg']}점, 편차: {d['student_score']-d['class_avg']:+.1f}점)
- 5대 평가 지표:
{metrics_str}
- 분기별 추이: {dict(zip(d['q_labels'],[f"{s}점" for s in d['q_scores']]))}
- 강사 메모: {d['memo']}
{exam_section}
[작성 규칙]
- 과도한 미사여구 없이 팩트 기반 교육 컨설턴트 톤 (~했습니다, ~할 예정입니다)
- 필수 3문단 구조:
  1문단(단원 연계성): 이번 달 단원의 핵심 개념 + 중·고등 연계성 (4~5줄)
  2문단(정밀 관찰): 반드시 위 [시험지 문항별 분석 결과]를 인용하여, 맞은 문항의 공통 특징, 틀린 문항의 오답 패턴, 풀이 습관을 구체적으로 서술 (시험지 분석 없으면 점수·지표 데이터 기반 서술) (5~6줄)
  3문단(로드맵): 다음 달 진도 계획 + 가정 연계 학습 제안 (3~4줄)

JSON·코드 없이 순수 텍스트 3문단만 출력하십시오."""}]

            # 이미지 파일 추가
            for fd in d.get("files_data",[]):
                if "image" in fd["type"]:
                    b64=base64.b64encode(fd["bytes"]).decode()
                    content.insert(0,{"type":"image",
                        "source":{"type":"base64","media_type":fd["type"],"data":b64}})

            msg=client.messages.create(model="claude-opus-4-6",max_tokens=900,
                messages=[{"role":"user","content":content}])
            return msg.content[0].text
        except Exception as e:
            return f"[Claude AI 오류: {e}]\n\n"+rule_based_comment(d)

    with st.spinner("✍️ 코멘트 생성 중..."):
        use_claude="Claude" in d["ai_mode"] and d["claude_key"]
        comment_text=claude_ai_comment(d) if use_claude else rule_based_comment(d)

    # ═══════════════════════════════════════════════════
    # [FIX 3] 프리미엄 차트 함수들
    # ═══════════════════════════════════════════════════
    def make_bar(d):
        """5대 지표 개별 비교 그룹 막대 차트"""
        cats   = list(d["metrics"].keys())
        vals   = list(d["metrics"].values())
        avg_v  = d["class_avg"]
        avg_est= [avg_v]*len(cats)  # 지표별 반 평균 추정

        colors=[]
        for v in vals:
            if v>=90:   colors.append(GOLD)
            elif v>=80: colors.append("#2471A3")
            elif v>=70: colors.append(GREEN)
            else:       colors.append(SILVER)   # 낮아도 중립 색상

        fig=go.Figure()
        fig.add_trace(go.Bar(
            name=d["student_name"], x=cats, y=vals,
            marker=dict(color=colors, line=dict(width=0),
                        cornerradius=6),
            text=[f"<b>{v}점</b>" for v in vals],
            textposition="outside", textfont=dict(size=13),
            width=0.38,
        ))
        fig.add_trace(go.Bar(
            name="반 평균", x=cats, y=avg_est,
            marker=dict(color="#CDD6E0", line=dict(width=0), cornerradius=6),
            text=[f"{int(avg_v)}점"]*len(cats),
            textposition="outside", textfont=dict(size=11, color="#888"),
            width=0.38,
        ))
        fig.add_hline(y=avg_v, line_dash="dot", line_color=SILVER,
                      line_width=1.5,
                      annotation_text=f"반 평균 {avg_v:.1f}점",
                      annotation_position="top left",
                      annotation_font=dict(size=11, color=SILVER))
        fig.update_layout(
            barmode="group", height=340,
            margin=dict(l=10,r=10,t=40,b=10),
            paper_bgcolor="white", plot_bgcolor="white",
            yaxis=dict(range=[0,115], showgrid=True, gridcolor="#F0F0F0",
                       ticksuffix="점", tickfont=dict(size=11)),
            xaxis=dict(tickfont=dict(size=12, family="Noto Sans KR", color="#333")),
            legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center",
                        font=dict(size=12)),
            font=dict(family="Noto Sans KR"),
            bargap=0.25, bargroupgap=0.06,
        )
        return fig

    def make_radar(d):
        """값 레이블 + 반평균 비교 레이더"""
        cats = list(d["metrics"].keys())
        vals = list(d["metrics"].values())
        avg  = d["class_avg"]
        avg_vals=[avg]*len(cats)
        cats_r=cats+[cats[0]]; vals_r=vals+[vals[0]]; avg_r=avg_vals+[avg_vals[0]]

        fig=go.Figure()
        # 만점 기준 배경
        fig.add_trace(go.Scatterpolar(
            r=[100]*len(cats)+[100], theta=cats_r,
            fill="toself", fillcolor="rgba(230,235,245,0.5)",
            line=dict(color="#D5DCE8",width=1), showlegend=False))
        # 반 평균
        fig.add_trace(go.Scatterpolar(
            r=avg_r, theta=cats_r,
            fill="toself", fillcolor="rgba(138,155,176,0.15)",
            line=dict(color=SILVER, width=1.5, dash="dot"),
            name="반 평균(추정)"))
        # 학생
        fig.add_trace(go.Scatterpolar(
            r=vals_r, theta=cats_r,
            fill="toself", fillcolor="rgba(201,168,76,0.18)",
            line=dict(color=GOLD, width=2.5),
            marker=dict(size=9, color=GOLD, line=dict(width=2,color="white")),
            text=[f"<b>{v}점</b>" for v in vals]+[f"<b>{vals[0]}점</b>"],
            textposition="top center", mode="lines+markers+text",
            textfont=dict(size=11, color=NAVY),
            name=d["student_name"]))
        fig.update_layout(
            polar=dict(
                bgcolor="white",
                radialaxis=dict(visible=True, range=[0,100],
                                tickvals=[25,50,75,100],
                                tickfont=dict(size=9,color="#bbb"),
                                gridcolor="#E8ECF2", linecolor="#E8ECF2"),
                angularaxis=dict(tickfont=dict(size=12,color=NAVY,
                                               family="Noto Sans KR"),
                                 linecolor="#D5DCE8")),
            height=350,
            margin=dict(l=60,r=60,t=40,b=40),
            paper_bgcolor="white", showlegend=True,
            legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center",
                        font=dict(size=11)),
            font=dict(family="Noto Sans KR"))
        return fig

    def make_trend(d):
        """그라디언트 영역 + 반평균 비교 추이"""
        labels,scores=d["q_labels"],d["q_scores"]
        avg=[d["class_avg"]]*len(labels)

        fig=go.Figure()
        # 목표 라인
        fig.add_hline(y=90, line_dash="dot", line_color=GOLD, line_width=1,
                      annotation_text="목표 90점",
                      annotation_font=dict(size=10,color=GOLD),
                      annotation_position="top right")
        # 반평균
        fig.add_trace(go.Scatter(x=labels,y=avg, mode="lines",
            line=dict(color=SILVER,width=1.5,dash="dot"),
            name=f"반 평균 {d['class_avg']:.1f}점"))
        # 학생 추이
        fig.add_trace(go.Scatter(x=labels,y=scores,
            mode="lines+markers+text",
            line=dict(color=NAVY2,width=3.5),
            marker=dict(size=11,color=NAVY2,
                        line=dict(width=2.5,color=GOLD)),
            text=[f"<b>{s:.1f}점</b>" for s in scores],
            textposition="top center", textfont=dict(size=13,color=NAVY),
            name=d["student_name"],
            fill="tozeroy", fillcolor="rgba(30,58,110,0.07)"))

        # 최고점 강조
        max_v=max(scores); max_i=scores.index(max_v)
        fig.add_annotation(x=labels[max_i],y=max_v+3,
            text=f"🏆 최고 {max_v:.1f}점",
            showarrow=False, font=dict(size=11,color=GOLD),
            bgcolor="white", bordercolor=GOLD, borderwidth=1, borderpad=4)

        fig.update_layout(height=290,
            margin=dict(l=10,r=10,t=30,b=10),
            paper_bgcolor="white", plot_bgcolor="white",
            yaxis=dict(range=[max(0,min(scores)-20),108],
                       showgrid=True,gridcolor="#F2F4F8",ticksuffix="점",
                       tickfont=dict(size=11)),
            xaxis=dict(tickfont=dict(size=12,family="Noto Sans KR")),
            legend=dict(orientation="h",y=1.1,x=0.5,xanchor="center",
                        font=dict(size=12)),
            font=dict(family="Noto Sans KR"))
        return fig

    # ═══════════════════════════════════════════════════
    # [FIX 4] 프리미엄 미리보기 레이아웃
    # ═══════════════════════════════════════════════════
    diff=d["student_score"]-d["class_avg"]
    glv,gcol=grade_info(d["student_score"])
    best_metric = max(d["metrics"], key=d["metrics"].get)
    best_score  = d["metrics"][best_metric]

    # 배너 — 학원명은 별도 줄로, 등급 배지는 우측 배치
    st.markdown(f"""
<div style="background:linear-gradient(135deg,{NAVY},{NAVY2});
     border-radius:14px;padding:22px 28px;margin-bottom:20px;
     border-left:6px solid {GOLD};">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <div style="font-size:11px;color:{GOLD2};letter-spacing:2px;margin-bottom:6px;">
        {d['academy_name']} · {d['class_name']} · {d['report_month']} 월간 성적표
      </div>
      <div style="font-size:26px;font-weight:900;color:white;font-family:'Noto Serif KR';">
        {d['student_name']} 학생
      </div>
      <div style="margin-top:7px;font-size:13px;color:{GOLD2};opacity:.9;">
        {d['student_school']} | {d['student_grade']} | 담당: {d['teacher_name']}
      </div>
    </div>
    <div style="text-align:center;background:rgba(255,255,255,0.12);
                border-radius:12px;padding:14px 20px;border:1px solid {GOLD}55;">
      <div style="font-size:10px;color:{GOLD2};margin-bottom:4px;letter-spacing:1px;">이번 달 등급</div>
      <div style="font-size:22px;font-weight:900;color:{GOLD};">{glv}</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # 요약 카드 3개 — 음수 편차 숨김, 대신 최고 영역 표시
    c1,c2,c3=st.columns(3)
    cards=[
        (c1,"학생 종합 점수",f"{d['student_score']:.1f}점", NAVY),
        (c2,"이번 달 반 평균",f"{d['class_avg']:.1f}점",     "#546e7a"),
        (c3,f"최고 강점 영역",  f"{best_metric}\n{best_score}점", GOLD),
    ]
    for col,lbl,val,clr in cards:
        with col:
            with st.container(border=True):
                parts=val.split("\n")
                main_val=parts[0]
                sub_val=parts[1] if len(parts)>1 else ""
                st.markdown(f"""
<div style="text-align:center;padding:8px 0">
  <div style="font-size:11px;color:#888;margin-bottom:6px;letter-spacing:.5px">{lbl}</div>
  <div style="font-size:{'28px' if sub_val else '38px'};font-weight:900;color:{clr};
              font-family:'Noto Serif KR';line-height:1.2">{main_val}</div>
  {"<div style='font-size:15px;font-weight:700;color:"+clr+";margin-top:2px'>"+sub_val+"</div>" if sub_val else ""}
</div>""",unsafe_allow_html=True)

    st.markdown("")

    # 차트: 막대(전폭)
    with st.container(border=True):
        st.markdown(f"#### 📊 5대 영역별 점수 비교 (학생 vs 반 평균)")
        st.plotly_chart(make_bar(d),use_container_width=True,
                        config={"displayModeBar":False})

    # 차트: 레이더 + 추이
    col_r, col_t = st.columns([1,1], gap="large")
    with col_r:
        with st.container(border=True):
            st.markdown("#### 🕸️ 역량 방사형 분포")
            st.plotly_chart(make_radar(d),use_container_width=True,
                            config={"displayModeBar":False})
    with col_t:
        with st.container(border=True):
            st.markdown("#### 📈 분기별 성적 향상 추이")
            st.plotly_chart(make_trend(d),use_container_width=True,
                            config={"displayModeBar":False})

    # 지표 뱃지
    with st.container(border=True):
        st.markdown("#### 🏷️ 5대 평가 지표 현황")
        badges=""
        for lbl,val in d["metrics"].items():
            cls=("b-gold" if val>=90 else "b-blue" if val>=80
                 else "b-green" if val>=70 else "b-orange")   # 하위도 orange(중립)
            badges+=f'<span class="badge {cls}">{lbl} &nbsp;<b>{val}점</b></span>'
        st.markdown(badges,unsafe_allow_html=True)

    # 시험지 분석 결과 표시
    if d.get("exam_analysis"):
        with st.container(border=True):
            st.markdown(f"#### 📖 시험지 문항별 분석 결과")
            st.info(d["exam_analysis"])

    # 코멘트
    mode_lbl=("Claude AI · 시험지 분석 포함" if use_claude and d.get("exam_analysis")
              else "Claude AI 생성" if use_claude else "규칙 기반 생성")
    with st.container(border=True):
        st.markdown(f"#### 📝 교육 전문가 심층 진단 "
                    f"<span style='font-size:11px;color:#aaa'>({mode_lbl})</span>",
                    unsafe_allow_html=True)
        for i,para in enumerate([p for p in comment_text.split("\n\n") if p.strip()],1):
            lbl=["📘 단원 연계성","🔍 정밀 관찰","🗺️ 다음 달 로드맵"][min(i-1,2)]
            st.markdown(f"**{lbl}**")
            st.markdown(f"> {para.strip()}")

    # ═══════════════════════════════════════════════════
    # HTML 프리미엄 리포트 생성
    # ═══════════════════════════════════════════════════
    def build_html(d, comment):
        W=640
        def fw(fig,h): fig.update_layout(width=W,height=h,autosize=False); return fig

        bar_h   = fw(make_bar(d),   310).to_html(full_html=False, include_plotlyjs="cdn",
                                                   config={"displayModeBar":False})
        radar_h = fw(make_radar(d), 300).to_html(full_html=False, include_plotlyjs=False,
                                                   config={"displayModeBar":False})
        trend_h = fw(make_trend(d), 260).to_html(full_html=False, include_plotlyjs=False,
                                                   config={"displayModeBar":False})

        diff  = d["student_score"]-d["class_avg"]
        glv,gcol = grade_info(d["student_score"])
        best_m = max(d["metrics"], key=d["metrics"].get)
        best_s = d["metrics"][best_m]

        rows=""
        for lbl,val in d["metrics"].items():
            filled=int(val/100*20)
            bar="■"*filled+"□"*(20-filled)
            grd=("최우수" if val>=90 else "우수" if val>=80
                 else "양호" if val>=70 else "성장중")
            gc=(GOLD if val>=90 else "#1A5276" if val>=80
                else GREEN if val>=70 else SILVER)
            rows+=(f"<tr>"
                   f"<td style='padding:9px 16px;font-weight:700;color:{NAVY};width:130px'>{lbl}</td>"
                   f"<td style='padding:9px 16px;font-size:11px;color:#aaa;letter-spacing:-0.5px;font-family:monospace'>{bar}</td>"
                   f"<td style='padding:9px 16px;font-weight:900;color:{NAVY};text-align:right;width:60px'>{val}점</td>"
                   f"<td style='padding:9px 16px;text-align:right;width:90px'>"
                   f"<span style='background:{gc}18;color:{gc};padding:3px 10px;"
                   f"border-radius:12px;font-size:11px;font-weight:700'>{grd}</span></td>"
                   f"</tr>")

        paras="".join(
            f"<p style='margin:0 0 18px 0;text-indent:1.2em;text-align:justify'>{p.strip()}</p>"
            for p in comment.split("\n\n") if p.strip())

        exam_section_html=""
        if d.get("exam_analysis"):
            exam_section_html=f"""
<div style="margin:20px 0;padding:16px 20px;background:#FAFBFE;
     border-left:4px solid {GOLD};border-radius:0 8px 8px 0">
  <div style="font-size:11pt;font-weight:800;color:{NAVY};margin-bottom:10px">
    📖 시험지 문항별 분석 결과
  </div>
  <div style="font-size:10.5pt;line-height:1.9;color:#444;white-space:pre-wrap">{d['exam_analysis']}</div>
</div>"""

        seal_svg=f"""
<svg width="88" height="88" viewBox="0 0 88 88" xmlns="http://www.w3.org/2000/svg">
  <circle cx="44" cy="44" r="42" fill="none" stroke="{GOLD}" stroke-width="2.5"
          stroke-dasharray="5 3"/>
  <circle cx="44" cy="44" r="34" fill="none" stroke="{GOLD}" stroke-width="1.2"/>
  <text x="44" y="36" text-anchor="middle" font-family="serif"
        font-size="9" fill="{GOLD}" font-weight="bold">{d['academy_name'][:4]}</text>
  <text x="44" y="50" text-anchor="middle" font-family="serif"
        font-size="9" fill="{GOLD}" font-weight="bold">성적 확인</text>
  <text x="44" y="62" text-anchor="middle" font-family="serif"
        font-size="8" fill="{GOLD}">CERTIFIED</text>
</svg>"""

        return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Noto Sans KR',sans-serif;background:#DDE2EC;padding:24px}}
@media print{{
  body{{background:white;padding:0}}
  .no-print{{display:none!important}}
  @page{{size:A4 portrait;margin:0}}
  .page{{box-shadow:none!important;margin:0!important;border-radius:0!important}}
}}
.page{{
  width:210mm;min-height:296mm;background:white;
  margin:0 auto 24px;padding:12mm 16mm 16mm;
  box-shadow:0 6px 28px rgba(11,31,75,0.16);
  page-break-after:always;position:relative;
  border-top:5px solid {GOLD};
}}
.page:last-child{{page-break-after:auto}}

/* 상단 골드 줄 장식 */
.page::before{{
  content:'';display:block;height:2px;
  background:linear-gradient(90deg,{GOLD},{GOLD2},{GOLD});
  margin-bottom:14px;border-radius:2px;
}}

.hdr{{
  background:linear-gradient(135deg,{NAVY},{NAVY2});
  color:white;border-radius:10px;padding:16px 22px;
  margin-bottom:16px;border-left:5px solid {GOLD};
}}
.hdr .ac{{font-size:9pt;opacity:.7;letter-spacing:2px;margin-bottom:4px;
           font-family:'Noto Sans KR'}}
.hdr .ti{{font-size:17pt;font-weight:900;font-family:'Noto Serif KR';
           letter-spacing:-0.3px}}
.hdr .sub{{font-size:10pt;opacity:.85;margin-top:5px;color:{GOLD2}}}

.sec{{font-size:12pt;font-weight:800;color:{NAVY};
       border-left:4px solid {GOLD};padding-left:10px;
       margin:16px 0 10px;font-family:'Noto Serif KR'}}

.srow{{display:flex;gap:10px;margin-bottom:16px}}
.sbox{{flex:1;text-align:center;border-radius:10px;padding:13px 8px;
        border:1.5px solid #DDE2EC;background:#FAFBFE}}
.sbox .lb{{font-size:9pt;color:#888;margin-bottom:5px;letter-spacing:.5px}}
.sbox .vl{{font-size:23pt;font-weight:900;font-family:'Noto Serif KR'}}

table.mt{{width:100%;border-collapse:collapse;background:#FAFBFE;
           border:1px solid #E8ECF4;border-radius:8px;overflow:hidden}}
table.mt tr{{border-bottom:1px solid #EEF1F8}}
table.mt tr:last-child{{border-bottom:none}}
table.mt tr:nth-child(even){{background:#F4F6FC}}

.cmt{{font-size:11pt;line-height:2.1;color:#333;
       border-top:3px solid {GOLD};padding-top:16px;
       font-family:'Noto Sans KR'}}

.ft{{position:absolute;bottom:10mm;left:16mm;right:16mm;
      display:flex;justify-content:space-between;align-items:center;
      border-top:1px solid {GOLD}44;padding-top:7px;font-size:8.5pt;color:#aaa}}

.pbtn{{display:block;width:300px;margin:0 auto 20px;
        background:{NAVY};color:white;border:none;
        padding:15px 30px;border-radius:12px;font-size:16px;font-weight:700;
        cursor:pointer;font-family:'Noto Sans KR';
        border-bottom:3px solid {GOLD}}}
.pbtn:hover{{background:{NAVY2}}}
.grade-badge{{display:inline-block;padding:4px 14px;border-radius:20px;
               font-size:13px;font-weight:700;color:white;
               background:{gcol};margin-left:10px;vertical-align:middle}}
</style></head><body>

<button class="pbtn no-print" onclick="window.print()">🖨️ A4 인쇄 / PDF 저장</button>

<!-- ═══ PAGE 1: 점수 요약 + 막대차트 + 지표표 ═══ -->
<div class="page">
  <div class="hdr" style="display:flex;justify-content:space-between;align-items:center;">
    <div>
      <div class="ac">{d['academy_name']} · {d['class_name']} · {d['report_month']} 월간 성적표</div>
      <div class="ti">{d['student_name']} 학생 학업 성취 리포트</div>
      <div class="sub">{d['student_school']} | {d['student_grade']} | 담당: {d['teacher_name']}</div>
    </div>
    <div style="text-align:center;background:rgba(255,255,255,0.12);
                border-radius:10px;padding:12px 18px;border:1px solid {GOLD}55;min-width:80px;">
      <div style="font-size:9pt;color:{GOLD2};margin-bottom:4px;">이번 달 등급</div>
      <div style="font-size:20pt;font-weight:900;color:{GOLD};">{glv}</div>
    </div>
  </div>

  <div class="srow">
    <div class="sbox">
      <div class="lb">학생 종합 점수</div>
      <div class="vl" style="color:{NAVY}">{d['student_score']:.1f}점</div>
    </div>
    <div class="sbox">
      <div class="lb">이번 달 반 평균</div>
      <div class="vl" style="color:#546e7a">{d['class_avg']:.1f}점</div>
    </div>
    <div class="sbox">
      <div class="lb">최고 강점 영역</div>
      <div style="font-size:13pt;font-weight:900;color:{GOLD};margin-top:4px;line-height:1.3">
        {best_m}<br><span style="font-size:16pt">{best_s}점</span></div>
    </div>
    <div class="sbox">
      <div class="lb">학습 단원</div>
      <div style="font-size:10pt;font-weight:700;color:{NAVY};margin-top:6px;
                  line-height:1.4">{d['subject']}</div>
    </div>
  </div>

  <div class="sec">📊 5대 영역별 점수 비교 (학생 vs 반 평균)</div>
  <div style="overflow:hidden;width:100%">{bar_h}</div>

  <div class="sec" style="margin-top:14px">🏷️ 5대 평가 지표 상세</div>
  <table class="mt">{rows}</table>

  <div class="ft">
    <span>{d['academy_name']}</span>
    <span>발행일 {datetime.now().strftime('%Y년 %m월 %d일')} · 1 / 3</span>
  </div>
</div>

<!-- ═══ PAGE 2: 레이더 + 추이 ═══ -->
<div class="page">
  <div class="hdr">
    <div class="ac">{d['academy_name']} · 역량 & 성장 분석</div>
    <div class="ti">{d['student_name']} 학생 — 학습 역량 심층 분석</div>
    <div class="sub">학습 단원: {d['subject']} | {d['report_month']}</div>
  </div>

  <div class="sec">🕸️ 5대 영역별 역량 방사형 분포</div>
  <div style="overflow:hidden;width:100%">{radar_h}</div>

  <div class="sec" style="margin-top:14px">📈 분기별 성적 향상 추이</div>
  <div style="overflow:hidden;width:100%">{trend_h}</div>

  <div class="ft">
    <span>{d['teacher_name']} 작성</span>
    <span>발행일 {datetime.now().strftime('%Y년 %m월 %d일')} · 2 / 3</span>
  </div>
</div>

<!-- ═══ PAGE 3: 코멘트 + 시험지분석 + 인장 ═══ -->
<div class="page">
  <div class="hdr">
    <div class="ac">{d['academy_name']} · 전문가 심층 진단</div>
    <div class="ti">{d['student_name']} 학생 — 학습 진단 & 로드맵</div>
    <div class="sub">담당: {d['teacher_name']} | {d['report_month']} 발행</div>
  </div>

  <div class="sec">📝 교육 전문가 심층 진단 코멘트</div>
  <div class="cmt">{paras}</div>

  {exam_section_html}

  <div style="display:flex;justify-content:flex-end;align-items:center;
              margin-top:24px;gap:20px">
    <div style="text-align:right">
      <div style="font-size:10pt;color:#888;margin-bottom:4px">담당 강사 확인</div>
      <div style="font-size:12pt;font-weight:700;color:{NAVY};
                  border-bottom:1px solid {NAVY};padding-bottom:4px;min-width:120px">
        {d['teacher_name']}
      </div>
    </div>
    {seal_svg}
  </div>

  <div class="ft">
    <span>{d['academy_name']} — 이 성적표는 학원 공식 발행 문서입니다.</span>
    <span>발행일 {datetime.now().strftime('%Y년 %m월 %d일')} · 3 / 3</span>
  </div>
</div>
</body></html>"""

    st.markdown("---")
    html_out = build_html(d, comment_text)
    b64_out  = base64.b64encode(html_out.encode("utf-8")).decode()
    fname    = f"성적표_{d['student_name']}_{d['report_month']}_{datetime.now().strftime('%m%d')}.html"

    c_dl, c_tip = st.columns([1,2])
    with c_dl:
        st.markdown(
            f'<a href="data:text/html;base64,{b64_out}" download="{fname}" '
            f'style="display:block;background:{NAVY};color:white;text-align:center;'
            f'padding:15px;border-radius:12px;font-size:16px;font-weight:700;'
            f'text-decoration:none;border-bottom:3px solid {GOLD}">'
            f'⬇️ 프리미엄 성적표 다운로드</a>',
            unsafe_allow_html=True)
    with c_tip:
        st.info("💡 다운로드 → Chrome/Safari로 열기 → **⌘+P** → 'PDF로 저장'\n\n"
                "A4 3페이지 (점수요약·차트·진단코멘트) 로 깔끔하게 출력됩니다.")
