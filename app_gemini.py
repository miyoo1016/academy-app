import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import base64, io
import google.generativeai as genai
from PIL import Image
import os

# ═══════════════════════════════════════════════════════
# 색상 팔레트 (프리미엄 차콜·골드 테마)
# ═══════════════════════════════════════════════════════
CHARCOAL  = "#36454F"
CHARCOAL2 = "#4A5D6A"
GOLD      = "#C9A84C"
GOLD2     = "#F0DFA0"
SILVER    = "#8A9BB0"
CREAM     = "#FAF9F6"
GREEN     = "#1B6B3A"
ORANGE    = "#C85000"
RED       = "#A31515"

def grade_info(score):
    if score >= 95: return "최우수", GOLD
    if score >= 90: return "우수",   "#1A5276"
    if score >= 85: return "우수",   "#1A5276"
    if score >= 80: return "양호",   "#1B6B3A"
    if score >= 75: return "양호",   "#1B6B3A"
    return "성장중", "#5D7A8C"

# ═══════════════════════════════════════════════════════
# 로고 처리 로직 (image_0.png 파일 필수)
# ═══════════════════════════════════════════════════════
def get_base64_from_image(image_path_or_file):
    buffered = io.BytesIO()
    if isinstance(image_path_or_file, str):
        with open(image_path_or_file, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    else:
        image_path_or_file.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

logo_path = 'image_0.png'
logo_img_html = ""
logo_base64 = ""

if os.path.exists(logo_path):
    try:
        academy_logo_img = Image.open(logo_path)
        logo_base64 = get_base64_from_image(academy_logo_img)
        logo_img_html = f'<img src="data:image/png;base64,{logo_base64}" style="height:55px; margin-right:20px; vertical-align:middle; border-radius:6px; background-color:white; padding:4px; box-shadow: 0px 2px 5px rgba(0,0,0,0.2);">'
    except Exception as e:
        print(f"Logo load error: {e}")

# ═══════════════════════════════════════════════════════
# 페이지 설정 & 전역 CSS
# ═══════════════════════════════════════════════════════
st.set_page_config(page_title="학원 성적표 v2", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
html, body, [class*="css"] {{ font-family:'Noto Sans KR',sans-serif; }}
.stApp {{ background:#EEF1F7; }}
.stButton>button {{ border-radius:10px; font-weight:700; font-size:15px; }}
div[data-testid="stSidebar"] {{ background:{CHARCOAL}; }}
div[data-testid="stSidebar"] * {{ color:white !important; }}
div[data-testid="stSidebar"] .stRadio label {{ color:{GOLD2} !important; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius:14px; box-shadow:0 2px 14px rgba(54,69,79,0.09); }}
.badge {{ display:inline-block; padding:5px 14px; border-radius:20px; font-size:12px; font-weight:700; margin:3px; }}
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
    st.markdown(f"<div style='color:{GOLD};font-size:18px;font-weight:900;margin-bottom:4px'>🏫 학원 정보</div>", unsafe_allow_html=True)
    academy_name   = "미래학원"
    st.text_input("학원명", value=academy_name, disabled=True)
    teacher_name   = "수학 선생님"
    st.text_input("담당 선생님", value=teacher_name, disabled=True)
    
    allowed_months = ["3월", "4월", "5월", "6월", "9월", "10월", "11-12월"]
    report_month   = st.selectbox("평가 월", allowed_months, index=0)
    
    st.markdown("---")
    st.markdown(f"<div style='color:{GOLD};font-size:18px;font-weight:900;margin-bottom:4px'>👤 학생 정보</div>", unsafe_allow_html=True)
    student_name   = st.text_input("학생 이름",   value="홍길동")
    student_grade  = st.selectbox("학년", ["초등 3학년","초등 4학년","초등 5학년","초등 6학년","중학교 1학년","중학교 2학년","중학교 3학년"])
    
    st.markdown("---")
    st.markdown(f"<div style='color:{GOLD};font-size:18px;font-weight:900;margin-bottom:4px'>🤖 AI 설정</div>", unsafe_allow_html=True)
    ai_mode = st.radio("코멘트 생성 방식", ["📝 규칙 기반 (무료)","🧠 Gemini AI (유료·고품질)"],index=0)
    gemini_key = ""
    if "Gemini" in ai_mode:
        gemini_key = st.text_input("Google Gemini API Key", type="password", placeholder="AIza...")

# ═══════════════════════════════════════════════════════
# 헤더
# ═══════════════════════════════════════════════════════
st.markdown(f"""
<div style="background:linear-gradient(135deg,{CHARCOAL},{CHARCOAL2});border-radius:16px;
     padding:20px 28px;margin-bottom:20px;
     border-bottom:4px solid {GOLD}; display:flex; align-items:center;">
  {logo_img_html}
  <span style="font-size:26px;font-weight:900;color:white;font-family:'Noto Serif KR'">
    📊 학원 성적표 v2 (Gemini 이식 버전)
  </span>
  <span style="font-size:14px;color:{GOLD2};margin-left:auto;">{academy_name}</span>
</div>""", unsafe_allow_html=True)

tab_input, tab_preview = st.tabs(["✏️ 성적 입력", "📋 성적표 미리보기 & 출력"])

# ═══════════════════════════════════════════════════════
# TAB 1: 성적 입력
# ═══════════════════════════════════════════════════════
with tab_input:
    with st.container(border=True):
        st.markdown(f"### 📎 시험지 업로드 <span style='font-size:13px;color:{GOLD};'>(Gemini AI 모드에서 문항별 분석 자동 반영)</span>", unsafe_allow_html=True)
        st.caption("JPG · PNG · PDF 지원 | 여러 장 동시 업로드 가능 | 파일 없이 수동 입력만으로도 생성 가능")
        uploaded_files = st.file_uploader("파일 선택", type=["jpg","jpeg","png","pdf"], accept_multiple_files=True, label_visibility="collapsed")
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
            st.markdown("### 📝 이번 달 점수 (2회 평가)")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                score1 = st.number_input("평가 1회 학생 점수", 0.0, 100.0, 85.0, 0.5, format="%.1f")
                avg1   = st.number_input("평가 1회 반 평균",   0.0, 100.0, 76.0, 0.5, format="%.1f")
            with col_s2:
                score2 = st.number_input("평가 2회 학생 점수", 0.0, 100.0, 88.0, 0.5, format="%.1f")
                avg2   = st.number_input("평가 2회 반 평균",   0.0, 100.0, 78.0, 0.5, format="%.1f")
            
            student_score = (score1 + score2) / 2
            class_avg = (avg1 + avg2) / 2
            
            st.info(f"💡 자동 계산된 월간 종합 평균 - 학생: **{student_score:.1f}점** / 반: **{class_avg:.1f}점**")
            subject = st.text_input("학습 단원/과목", value="분수와 소수의 혼합 계산")
            
            st.markdown(f"#### 🎯 5대 평가 지표 (5점 단위)")
            m1 = st.slider("① 수업태도",       0, 100, 90, step=5)
            m2 = st.slider("② 과제수행",       0, 100, 85, step=5)
            m3 = st.slider("③ 계산력(연산)",   0, 100, 90, step=5)
            m4 = st.slider("④ 심화문제풀이",   0, 100, 75, step=5)
            m5 = st.slider("⑤ 학업성취도",     0, 100, 85, step=5)

    with col_R:
        with st.container(border=True):
            st.markdown("### 📈 월별 성적 추이")
            st.caption("점수가 있는 달의 데이터를 입력하세요. (엑셀처럼 표에서 직접 수정 가능)")
            
            cur_month = datetime.now().month
            if cur_month in [11, 12]:
                cur_month_str = "11-12월"
            elif f"{cur_month}월" in allowed_months:
                cur_month_str = f"{cur_month}월"
            else:
                cur_month_str = ""

            trend_data = []
            for m_label in allowed_months:
                trend_data.append({
                    "월": m_label,
                    "학생 점수": float(student_score) if m_label == cur_month_str else 0.0,
                    "반 평균": float(class_avg) if m_label == cur_month_str else 0.0
                })
            df_trend = pd.DataFrame(trend_data)
            
            edited_df = st.data_editor(
                df_trend,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "월": st.column_config.TextColumn("월", disabled=True),
                    "학생 점수": st.column_config.NumberColumn("학생 점수", min_value=0.0, max_value=100.0, format="%.1f", step=0.5),
                    "반 평균": st.column_config.NumberColumn("반 평균", min_value=0.0, max_value=100.0, format="%.1f", step=0.5)
                }
            )
            
            q_labels, q_scores, q_avgs = [], [], []
            for _, row in edited_df.iterrows():
                if row["학생 점수"] > 0:
                    q_labels.append(row["월"])
                    q_scores.append(row["학생 점수"])
                    q_avgs.append(row["반 평균"])
            
            if not q_scores:
                fallback_label = cur_month_str if cur_month_str else allowed_months[0]
                q_labels = [fallback_label]
                q_scores = [float(student_score)]
                q_avgs = [float(class_avg)]

            st.markdown("#### 📌 강사 관찰 메모")
            memo = st.text_area("", value="분수 나눗셈 역수 개념 정착 확인. 심화문제 3번 패턴 반복 오류 있음.", height=150, label_visibility="collapsed")

    st.markdown("")
    gen_btn = st.button("🚀 성적표 생성하기", use_container_width=True, type="primary")

    if gen_btn:
        files_data = []
        for f in (uploaded_files or []):
            files_data.append({"name":f.name,"type":f.type,"bytes":f.getvalue()})

        exam_analysis = None
        if "Gemini" in ai_mode and gemini_key and files_data:
            img_files = [fd for fd in files_data if "image" in fd["type"]]
            if img_files:
                with st.spinner("📖 시험지 문항별 분석 중 (Gemini Vision)..."):
                    try:
                        genai.configure(api_key=gemini_key)
                        model = genai.GenerativeModel('gemini-2.5-flash')
                        
                        content = ["""이 수학 시험지를 꼼꼼히 분석하세요.
아래 항목을 **한국어**로 정확하게 파악하여 서술하세요:
1. **맞은 문항**: 정답 표시가 있는 문항 번호
2. **틀린 문항**: 오답 표시가 있는 문항 번호
3. **오답 패턴 분석**: 틀린 문제들의 공통 유형 
4. **강점 유형**: 맞은 문제들의 공통 특징
5. **풀이 습관**: 풀이 과정 기재 여부, 검산 흔적 등"""]
                        for fd in img_files:
                            content.append(Image.open(io.BytesIO(fd["bytes"])))
                        
                        res = model.generate_content(content)
                        exam_analysis = res.text
                        st.success("✅ 시험지 분석 완료")
                    except Exception as e:
                        exam_analysis = None
                        st.warning(f"시험지 분석 실패: {e}")

        st.session_state["report_data"] = dict(
            academy_name=academy_name, teacher_name=teacher_name,
            report_month=report_month,
            student_name=student_name, student_grade=student_grade,
            score1=float(score1), score2=float(score2),
            avg1=float(avg1), avg2=float(avg2),
            student_score=float(student_score), class_avg=float(class_avg),
            subject=subject,
            metrics={"수업태도":m1,"과제수행":m2,"계산력(연산)":m3,
                     "심화문제풀이":m4,"학업성취도":m5},
            q_scores=[float(s) for s in q_scores], q_avgs=[float(a) for a in q_avgs], q_labels=q_labels,
            memo=memo, ai_mode=ai_mode, gemini_key=gemini_key,
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

    def rule_based_comment(d):
        s,avg = d["student_score"],d["class_avg"]
        m,diff = d["metrics"],s-avg
        subj,grade = d["subject"],d["student_grade"]

        if "분수" in subj or "소수" in subj:
            p1=(f"이번 달 학습 단원 '{subj}'은(는) {grade} 수학의 핵심 개념으로, 분수·소수 간 변환과 사칙연산 응용 능력을 동시에 요구합니다. 이 단원은 단순 계산 능숙도뿐 아니라 원리 이해까지 함께 체화하는 것이 장기적으로 중요합니다.")
        elif "도형" in subj or "넓이" in subj or "부피" in subj:
            p1=(f"이번 달 학습 단원 '{subj}'은(는) 공간 감각과 논리적 추론 능력을 동시에 훈련하는 단원입니다. 공식 암기에 그치지 않고 도형의 성질과 원리를 시각적으로 이해하는 방향으로 지도하고 있습니다.")
        else:
            p1=(f"이번 달 학습 단원 '{subj}'은(는) {grade} 수학 과정의 주요 주제로 논리적 사고력과 연산 정확도를 함께 요구합니다. 풀이 과정을 단계적으로 서술하는 습관을 함께 기르도록 지도하고 있습니다.")

        weak   = [k for k,v in m.items() if v<75]
        strong = [k for k,v in m.items() if v>=90]
        obs=[]
        if diff>=10:
            obs.append(f"{d['student_name']} 학생은 종합 평균에서 반 평균 대비 {diff:+.1f}점으로 우수한 성취를 기록했습니다.")
        elif diff>=0:
            obs.append(f"종합 평균 점수는 반 평균 대비 {diff:+.1f}점으로 안정적인 학습 성취를 유지하고 있습니다.")
        else:
            obs.append(f"종합 평균 점수가 반 평균보다 {diff:.1f}점 낮아 집중 보완이 필요한 상황입니다.")
        if strong:
            obs.append(f"5대 지표 중 {', '.join(strong)} 영역에서 90점 이상의 뛰어난 역량을 보이고 있습니다.")
        if weak:
            obs.append(f"반면 {', '.join(weak)} 영역은 보완이 필요하며, 관련 유형의 반복 훈련을 강화하고 있습니다.")
        if d["memo"]:
            obs.append(f"수업 중 관찰 내용: {d['memo']}")
        p2=" ".join(obs)

        qs=d["q_scores"]
        if len(qs) >= 2:
            if qs[-1]>qs[-2]: tmsg=f"이전 평가 대비 {qs[-1]-qs[-2]:+.1f}점 향상된 흐름입니다."
            elif qs[-1]<qs[-2]: tmsg=f"이전 평가 대비 하락하였으나, 개념 보완으로 회복 가능합니다."
            else: tmsg="꾸준한 학습 흐름을 유지하고 있습니다."
        else:
            tmsg="성공적으로 학습 기록이 누적되고 있습니다."

        p3=(f"{tmsg} 다음 달에는 '{subj}' 단원 응용 심화 문제 풀이 확장과 이전 단원 연계 복습을 병행할 예정입니다. 가정 내 복습 루틴을 함께 유지해 주시면 감사하겠습니다.")

        if d.get("exam_analysis"):
            exam_txt = d["exam_analysis"]
            p2 = (p2 + f"\n\n업로드된 시험지를 문항별로 분석한 결과: {exam_txt}")

        return f"{p1}\n\n{p2}\n\n{p3}"

    def gemini_ai_comment(d):
        try:
            genai.configure(api_key=d["gemini_key"])
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            metrics_str="\n".join(f"  - {k}: {v}점" for k,v in d["metrics"].items())
            exam_section = ""
            if d.get("exam_analysis"):
                exam_section = f"\n[시험지 문항별 분석 결과 — 반드시 2문단에 구체적으로 반영할 것]\n{d['exam_analysis']}\n"
            content=[f"""당신은 수학 전문 학원 강사입니다. 학부모 상담용 리포트를 작성하십시오.

[학생 데이터]
- 이름: {d['student_name']}
- 단원: {d['subject']}
- 평가 1회: 학생 {d['score1']}점 / 평균 {d['avg1']}점
- 평가 2회: 학생 {d['score2']}점 / 평균 {d['avg2']}점
- 종합 평균: 학생 {d['student_score']}점 / 평균 {d['class_avg']}점
- 5대 평가 지표:
{metrics_str}
- 강사 메모: {d['memo']}{exam_section}
[작성 규칙]
- 과도한 미사여구 없이 팩트 기반 교육 컨설턴트 톤 (~했습니다, ~할 예정입니다)
- 필수 3문단 구조:
  1문단: 이번 달 단원 핵심 개념 (3~4줄)
  2문단: 1회/2회 평가 결과 추이 및 지표 기반 정밀 관찰 (시험지 분석 포함 시 구체적 서술) (5~6줄)
  3문단: 다음 달 진도 계획 및 로드맵 (3줄)

순수 텍스트 3문단만 출력하십시오."""]

            for fd in d.get("files_data",[]):
                if "image" in fd["type"]:
                    content.append(Image.open(io.BytesIO(fd["bytes"])))

            res = model.generate_content(content)
            return res.text
        except Exception as e:
            return f"[Gemini AI 오류: {e}]\n\n"+rule_based_comment(d)

    with st.spinner("✍️ 코멘트 생성 중..."):
        use_ai="Gemini" in d["ai_mode"] and d["gemini_key"]
        comment_text=gemini_ai_comment(d) if use_ai else rule_based_comment(d)

    # ═══════════════════════════════════════════════════
    # 차트 함수
    # ═══════════════════════════════════════════════════
    def make_radar(d):
        cats = list(d["metrics"].keys())
        vals = list(d["metrics"].values())
        cats_r=cats+[cats[0]]; vals_r=vals+[vals[0]]

        fig=go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=[100]*len(cats)+[100], theta=cats_r,
            fill="toself", fillcolor="rgba(230,235,245,0.5)",
            line=dict(color="#D5DCE8",width=1), showlegend=False))
        
        fig.add_trace(go.Scatterpolar(
            r=vals_r, theta=cats_r,
            fill="toself", fillcolor="rgba(201,168,76,0.18)",
            line=dict(color=GOLD, width=2.5),
            marker=dict(size=9, color=GOLD, line=dict(width=2,color="white")),
            text=[f"<b>{v}점</b>" for v in vals]+[f"<b>{vals[0]}점</b>"],
            textposition="top center", mode="lines+markers+text",
            textfont=dict(size=13, color=CHARCOAL),
            name=d["student_name"]))
            
        fig.update_layout(
            polar=dict(
                bgcolor="white",
                radialaxis=dict(visible=True, range=[0,100], tickvals=[25,50,75,100],
                                tickfont=dict(size=9,color="#bbb"),
                                gridcolor="#E8ECF2", linecolor="#E8ECF2"),
                angularaxis=dict(tickfont=dict(size=14,color=CHARCOAL, family="Noto Sans KR"),
                                 linecolor="#D5DCE8")),
            height=420, margin=dict(l=30,r=30,t=30,b=30),
            paper_bgcolor="white", showlegend=False,
            font=dict(family="Noto Sans KR"))
        return fig

    def make_trend(d):
        labels, scores, avgs = d["q_labels"], d["q_scores"], d["q_avgs"]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=labels, y=avgs, mode="lines+markers",
            line=dict(color=SILVER, width=1.5, dash="dot"),
            marker=dict(size=6, color=SILVER),
            name=f"해당 월 반 평균"))
            
        fig.add_trace(go.Scatter(
            x=labels, y=scores,
            mode="lines+markers+text",
            line=dict(color=CHARCOAL2, width=3),
            marker=dict(size=10, color=CHARCOAL2, line=dict(width=2.5, color=GOLD)),
            text=[f"{s:.1f}점" for s in scores],
            textposition="top center",
            textfont=dict(size=11, color=CHARCOAL),
            name=d["student_name"],
            fill="tozeroy", fillcolor="rgba(74,93,106,0.1)"))

        ymin = max(0, min(scores) - 15) if scores else 0
        fig.update_layout(
            height=300, margin=dict(l=55, r=20, t=40, b=60),
            paper_bgcolor="white", plot_bgcolor="white",
            yaxis=dict(range=[ymin, 112], showgrid=True, gridcolor="#F2F4F8",
                       tickmode="array", tickvals=[0, 20, 40, 60, 80, 100],
                       ticktext=["0점","20점","40점","60점","80점","100점"],
                       tickfont=dict(size=11)),
            xaxis=dict(tickfont=dict(size=11, family="Noto Sans KR"), automargin=True),
            legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center", font=dict(size=11)),
            font=dict(family="Noto Sans KR"))
        return fig

    # ═══════════════════════════════════════════════════
    # 미리보기 렌더링 - 웹 화면용
    # ═══════════════════════════════════════════════════
    glv,gcol=grade_info(d["student_score"])
    best_metric = max(d["metrics"], key=d["metrics"].get)
    best_score  = d["metrics"][best_metric]

    st.markdown(f"""
<div style="background:linear-gradient(135deg,{CHARCOAL},{CHARCOAL2});
     border-radius:14px;padding:22px 28px;margin-bottom:20px;
     border-left:6px solid {GOLD}; display:flex; align-items:center;">
  {logo_img_html}
  <div>
    <div style="font-size:18px;font-weight:700;color:{GOLD2};letter-spacing:1px;margin-bottom:6px;">
      {d['academy_name']} · {d['report_month']} 성적표
    </div>
    <div style="font-size:30px;font-weight:900;color:white;font-family:'Noto Serif KR';">
      {d['student_name']} 학생 성적표 미리보기
    </div>
    <div style="margin-top:7px;font-size:15px;color:{GOLD2};opacity:.9;">
      {d['student_grade']} | 담당: {d['teacher_name']}
    </div>
  </div>
  <div style="text-align:center;background:rgba(255,255,255,0.12);
              border-radius:12px;padding:14px 20px;border:1px solid {GOLD}55;margin-left:auto;margin-right:0;">
    <div style="font-size:10px;color:{GOLD2};margin-bottom:4px;letter-spacing:1px;">월간 종합 등급</div>
    <div style="font-size:22px;font-weight:900;color:{GOLD};">{glv}</div>
  </div>
</div>""", unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    cards=[
        (c1,"평가 1회 (학생/평균)", f"{d['score1']:.1f} / {d['avg1']:.1f}", CHARCOAL),
        (c2,"평가 2회 (학생/평균)", f"{d['score2']:.1f} / {d['avg2']:.1f}", CHARCOAL),
        (c3,"월간 종합 학생 평균", f"{d['student_score']:.1f}점", "#546e7a"),
        (c4,f"최고 강점 영역",  f"{best_metric}\n{best_score}점", GOLD),
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
  <div style="font-size:{'20px' if sub_val else '22px'};font-weight:900;color:{clr};
              font-family:'Noto Serif KR';line-height:1.2">{main_val}</div>
  {"<div style='font-size:14px;font-weight:700;color:"+clr+";margin-top:2px'>"+sub_val+"</div>" if sub_val else ""}
</div>""",unsafe_allow_html=True)

    st.markdown("")

    col_r, col_t = st.columns([1,1], gap="large")
    with col_r:
        with st.container(border=True):
            st.markdown("#### 🕸️ 역량 방사형 분포")
            st.plotly_chart(make_radar(d),use_container_width=True, config={"displayModeBar":False})
    with col_t:
        with st.container(border=True):
            st.markdown("#### 📈 월별 종합 성적 향상 추이")
            st.plotly_chart(make_trend(d),use_container_width=True, config={"displayModeBar":False})

    with st.container(border=True):
        st.markdown("#### 🏷️ 5대 평가 지표 상세")
        badges=""
        for lbl,val in d["metrics"].items():
            cls=("b-gold" if val>=90 else "b-blue" if val>=80 else "b-green" if val>=70 else "b-orange")
            badges+=f'<span class="badge {cls}">{lbl} &nbsp;<b>{val}점</b></span>'
        st.markdown(badges,unsafe_allow_html=True)

    if d.get("exam_analysis"):
        with st.container(border=True):
            st.markdown(f"#### 📖 시험지 문항별 분석 결과")
            st.info(d["exam_analysis"])

    mode_lbl=("Gemini AI · 시험지 분석 포함" if use_ai and d.get("exam_analysis") else "Gemini AI 생성" if use_ai else "규칙 기반 생성")
    with st.container(border=True):
        # [수정] 웹 화면의 섹션 타이틀 변경
        st.markdown(f"#### 📝 월별 학습 진단 <span style='font-size:11px;color:#aaa'>({mode_lbl})</span>", unsafe_allow_html=True)
        for i,para in enumerate([p for p in comment_text.split("\n\n") if p.strip()],1):
            lbl=["📘 단원 연계성","🔍 정밀 관찰","🗺️ 다음 달 로드맵"][min(i-1,2)]
            st.markdown(f"**{lbl}**")
            st.markdown(f"> {para.strip()}")

    # ═══════════════════════════════════════════════════
    # HTML 출력
    # ═══════════════════════════════════════════════════
    def build_html(d, comment):
        W = 560
        def fw(fig, h):
            fig.update_layout(width=W, height=h, autosize=False, margin=dict(l=55, r=15, t=45, b=60), font=dict(size=10, family="Noto Sans KR"))
            return fig

        radar_h = fw(make_radar(d), 360).to_html(full_html=False, include_plotlyjs="cdn", config={"displayModeBar":False})
        trend_h = fw(make_trend(d), 240).to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar":False})

        glv,gcol = grade_info(d["student_score"])
        best_m = max(d["metrics"], key=d["metrics"].get)
        best_s = d["metrics"][best_m]

        logo_img_print_html = f'<img src="data:image/png;base64,{logo_base64}" style="height:45px;margin-right:15px;vertical-align:middle;border-radius:4px">' if logo_img_html else ""

        rows=""
        for lbl,val in d["metrics"].items():
            filled=int(val/100*20)
            bar="■"*filled+"□"*(20-filled)
            grd=("최우수" if val>=90 else "우수" if val>=80 else "양호" if val>=70 else "성장중")
            gc=(GOLD if val>=90 else "#1F516A" if val>=80 else GREEN if val>=70 else SILVER)
            rows+=(f"<tr>"
                   f"<td style='padding:9px 16px;font-weight:700;color:{CHARCOAL};width:130px'>{lbl}</td>"
                   f"<td style='padding:9px 16px;font-size:11px;color:#aaa;letter-spacing:-0.5px;font-family:monospace'>{bar}</td>"
                   f"<td style='padding:9px 16px;font-weight:900;color:{CHARCOAL};text-align:right;width:60px'>{val}점</td>"
                   f"<td style='padding:9px 16px;text-align:right;width:90px'>"
                   f"<span style='background:{gc}18;color:{gc};padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700'>{grd}</span></td>"
                   f"</tr>")

        paras="".join(f"<p style='margin:0 0 18px 0;text-indent:1.2em;text-align:justify'>{p.strip()}</p>" for p in comment.split("\n\n") if p.strip())

        exam_section_html=""
        if d.get("exam_analysis"):
            exam_section_html=f"""
<div style="margin:20px 0;padding:16px 20px;background:#FAFBFE;border-left:4px solid {GOLD};border-radius:0 8px 8px 0">
  <div style="font-size:11pt;font-weight:800;color:{CHARCOAL};margin-bottom:10px">📖 시험지 문항별 분석 결과</div>
  <div style="font-size:10.5pt;line-height:1.9;color:#444;white-space:pre-wrap">{d['exam_analysis']}</div>
</div>"""

        seal_svg=f"""
<svg width="88" height="88" viewBox="0 0 88 88" xmlns="http://www.w3.org/2000/svg">
  <circle cx="44" cy="44" r="42" fill="none" stroke="{GOLD}" stroke-width="2.5" stroke-dasharray="5 3"/>
  <circle cx="44" cy="44" r="34" fill="none" stroke="{GOLD}" stroke-width="1.2"/>
  <text x="44" y="36" text-anchor="middle" font-family="serif" font-size="9" fill="{GOLD}" font-weight="bold">{d['academy_name'][:4]}</text>
  <text x="44" y="50" text-anchor="middle" font-family="serif" font-size="9" fill="{GOLD}" font-weight="bold">성적 확인</text>
  <text x="44" y="62" text-anchor="middle" font-family="serif" font-size="8" fill="{GOLD}">CERTIFIED</text>
</svg>"""

        return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Noto Sans KR',sans-serif;background:#DDE2EC;padding:20px}}
@media print{{
  body{{background:white!important;padding:0!important}}
  .no-print{{display:none!important}}
  @page{{size:A4 portrait;margin:12mm 12mm 14mm 12mm}}
  .page{{box-shadow:none!important;margin:0!important;border-radius:0!important;width:100%!important;min-height:auto!important;padding:0!important;border-top:4px solid {GOLD}!important;}}
  .page::before{{display:none!important}}
}}
.page{{width:210mm;min-height:296mm;background:white;margin:0 auto 20px;padding:10mm 14mm 20mm;box-shadow:0 4px 24px rgba(11,31,75,0.14);page-break-after:always;position:relative;border-top:5px solid {GOLD};}}
.page:last-child{{page-break-after:auto}}
.page::before{{content:'';display:block;height:2px;background:linear-gradient(90deg,{GOLD},{GOLD2},{GOLD});margin-bottom:10px;border-radius:1px;}}
.hdr{{background:linear-gradient(135deg,{CHARCOAL},{CHARCOAL2});color:white;border-radius:8px;padding:12px 18px;margin-bottom:12px;border-left:4px solid {GOLD};display:flex;justify-content:space-between;align-items:center;}}

.hdr-left .ac{{font-size:14pt;font-weight:800;color:{GOLD2};letter-spacing:1px;margin-bottom:4px}}
.hdr-left .ti{{font-size:22pt;font-weight:900;font-family:'Noto Serif KR';margin-bottom:4px}}
.hdr-left .sub{{font-size:12pt;color:{GOLD2};opacity:.9;margin-top:4px}}

.hdr-grade{{text-align:center;background:rgba(255,255,255,0.12);border-radius:8px;padding:8px 14px;border:1px solid {GOLD}55;min-width:70px;flex-shrink:0;margin-left:12px}}
.hdr-grade .glb{{font-size:8pt;color:{GOLD2};margin-bottom:3px}}
.hdr-grade .gvl{{font-size:16pt;font-weight:900;color:{GOLD}}}
.sec{{font-size:10.5pt;font-weight:800;color:{CHARCOAL};border-left:3px solid {GOLD};padding-left:9px;font-family:'Noto Serif KR'}}
.srow{{display:flex;gap:8px}}
.sbox{{flex:1;text-align:center;border-radius:8px;padding:10px 6px;border:1.5px solid #DDE2EC;background:#FAFBFE;overflow:hidden}}
.sbox .lb{{font-size:8pt;color:#888;margin-bottom:4px;letter-spacing:.3px}}
.sbox .vl{{font-size:15pt;font-weight:900;font-family:'Noto Serif KR';white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.sbox .sm{{font-size:10pt;font-weight:700;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
table.mt{{width:100%;border-collapse:collapse;background:#FAFBFE;border:1px solid #E8ECF4;overflow:hidden}}
table.mt tr{{border-bottom:1px solid #EEF1F8}}
table.mt tr:last-child{{border-bottom:none}}
table.mt tr:nth-child(even){{background:#F4F6FC}}
table.mt td{{font-size:9.5pt;padding:7px 10px;white-space:nowrap}}
.cmt{{font-size:10.5pt;line-height:1.95;color:#333;border-top:3px solid {GOLD};padding-top:12px}}
.cmt p{{margin:0 0 14px 0;text-indent:1em;text-align:justify}}
.ft{{position:absolute;bottom:6mm;left:14mm;right:14mm;display:flex;justify-content:space-between;align-items:center;border-top:1px solid {GOLD}44;padding-top:5px;font-size:8pt;color:#aaa}}
</style></head><body>

<div class="page">
  <div class="hdr">
    <div class="hdr-left" style="display:flex; align-items:center;">
      {logo_img_print_html}
      <div>
        <div class="ac"><b>{d['academy_name']}</b> · {d['report_month']} 성적표</div>
        <div class="ti">{d['student_name']} 학생 학업 성취 리포트</div>
        <div class="sub">{d['student_grade']} | 담당: {d['teacher_name']}</div>
      </div>
    </div>
    <div class="hdr-grade"><div class="glb">월간 종합 등급</div><div class="gvl">{glv}</div></div>
  </div>

  <div class="srow" style="margin-top: 35px; margin-bottom: 50px;">
    <div class="sbox"><div class="lb">평가 1회 (학생/평균)</div><div class="vl" style="color:{CHARCOAL}">{d['score1']:.1f} / {d['avg1']:.1f}</div></div>
    <div class="sbox"><div class="lb">평가 2회 (학생/평균)</div><div class="vl" style="color:{CHARCOAL}">{d['score2']:.1f} / {d['avg2']:.1f}</div></div>
    <div class="sbox"><div class="lb">월간 종합 학생 평균</div><div class="vl" style="color:#546e7a">{d['student_score']:.1f}점</div></div>
    <div class="sbox"><div class="lb">최고 강점 영역</div><div class="sm" style="color:{GOLD}">{best_m}</div><div class="vl" style="color:{GOLD}">{best_s}점</div></div>
  </div>

  <div class="sec" style="margin-bottom: 20px;">🏷️ 5대 평가 지표 상세</div>
  <table class="mt" style="margin-bottom: 50px;">{rows}</table>

  <div class="sec" style="margin-bottom: 20px;">🕸️ 5대 영역별 역량 방사형 분포</div>
  <div style="overflow:hidden;width:100%">{radar_h}</div>

  <div class="ft">
    <span>{d['academy_name']}</span>
    <span>발행일 {datetime.now().strftime('%Y년 %m월 %d일')} · 1 / 2</span>
  </div>
</div>

<div class="page">
  <div class="hdr">
    <div class="hdr-left" style="display:flex; align-items:center;">
      {logo_img_print_html}
      <div>
        <div class="ac"><b>{d['academy_name']}</b> · {d['report_month']} 성적표</div>
        <div class="ti">{d['student_name']} 학생 — 학습 진단 &amp; 로드맵</div>
        <div class="sub">학습 단원: {d['subject']} | 담당: {d['teacher_name']}</div>
      </div>
    </div>
  </div>

  <div class="sec" style="margin-top: 25px; margin-bottom: 20px;">📈 월별 성적 향상 추이</div>
  <div style="overflow:hidden;width:100%; margin-bottom: 40px;">{trend_h}</div>

  <div class="sec" style="margin-bottom: 20px;">📝 월별 학습 진단</div>
  <div class="cmt">{paras}</div>

  {exam_section_html}

  <div style="display:flex;justify-content:flex-end;align-items:center;margin-top:40px;gap:16px">
    <div style="text-align:right">
      <div style="font-size:9pt;color:#888;margin-bottom:4px">담당 강사 확인</div>
      <div style="font-size:11pt;font-weight:700;color:{CHARCOAL};border-bottom:1px solid {CHARCOAL};padding-bottom:4px;min-width:110px">{d['teacher_name']}</div>
    </div>
    {seal_svg}
  </div>

  <div class="ft">
    <span>{d['academy_name']} — 학원 공식 발행 문서</span>
    <span>발행일 {datetime.now().strftime('%Y년 %m월 %d일')} · 2 / 2</span>
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
            f'style="display:block;background:{CHARCOAL};color:white;text-align:center;'
            f'padding:15px;border-radius:12px;font-size:16px;font-weight:700;'
            f'text-decoration:none;border-bottom:3px solid {GOLD}">'
            f'⬇️ 프리미엄 성적표 다운로드</a>', unsafe_allow_html=True)