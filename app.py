import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import base64, io
import google.generativeai as genai
from PIL import Image
import os
# from html2image import Html2Image # 가동성 확보를 위해 지연 임포트 사용

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
        logo_img_html = f'<img src="data:image/png;base64,{logo_base64}" style="height:45px; margin-right:20px; vertical-align:middle; border-radius:6px; background-color:white; padding:4px; box-shadow: 0px 2px 5px rgba(0,0,0,0.2);">'
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
    # [수정] 원생 정보
    st.markdown(f"<div style='color:{GOLD};font-size:18px;font-weight:900;margin-bottom:4px'>👤 원생 정보</div>", unsafe_allow_html=True)
    student_name   = st.text_input("원생 이름",   value="홍길동")
    student_grade  = st.selectbox("학년", ["초등 1학년","초등 2학년","초등 3학년","초등 4학년","초등 5학년","초등 6학년","중학교 1학년","중학교 2학년","중학교 3학년"])
    
    st.markdown("---")
    st.markdown(f"<div style='color:{GOLD};font-size:18px;font-weight:900;margin-bottom:4px'>🤖 AI 설정</div>", unsafe_allow_html=True)
    ai_mode = st.radio("코멘트 생성 방식", ["📝 규칙 기반 (무료)","🧠 Gemini AI (유료·고품질)"],index=0)
    if "Gemini" in ai_mode:
        gemini_key = st.text_input("Google Gemini API Key", type="password", placeholder="AIza...")

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
    📊 학원 성적표 v2.1.3 (배포 테스트 중...)
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
                # [수정] 원생 점수
                score1 = st.number_input("평가 1회 원생 점수", 0.0, 100.0, 85.0, 0.5, format="%.1f")
                avg1   = st.number_input("평가 1회 반 평균",   0.0, 100.0, 76.0, 0.5, format="%.1f")
            with col_s2:
                score2 = st.number_input("평가 2회 원생 점수", 0.0, 100.0, 88.0, 0.5, format="%.1f")
                avg2   = st.number_input("평가 2회 반 평균",   0.0, 100.0, 78.0, 0.5, format="%.1f")
            
            student_score = (score1 + score2) / 2
            class_avg = (avg1 + avg2) / 2
            
            st.info(f"💡 자동 계산된 월간 종합 평균 - 원생: **{student_score:.1f}점** / 반: **{class_avg:.1f}점**")
            
            st.markdown(f"#### <span style='color:{RED};'>💡 학습 단원 및 진도 설정 (필수)</span>", unsafe_allow_html=True)
            subject = st.text_input("이번 달 학습 단원/과목", value="분수와 소수의 혼합 계산")
            next_subject = st.text_input("다음 달 진도/과정", value="비례식과 비례배분")
            
            st.markdown("---")
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
            
            # 평가 월 기준으로 기본값 설정 (시스템 날짜 대신 사이드바 선택값 사용)
            eval_month_str = report_month

            trend_data = []
            for m_label in allowed_months:
                trend_data.append({
                    "월": m_label,
                    "원생 점수": float(student_score) if m_label == eval_month_str else 0.0,
                    "반 평균": float(class_avg) if m_label == eval_month_str else 0.0
                })
            df_trend = pd.DataFrame(trend_data)
            
            edited_df = st.data_editor(
                df_trend,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "월": st.column_config.TextColumn("월", disabled=True),
                    "원생 점수": st.column_config.NumberColumn("원생 점수", min_value=0.0, max_value=100.0, format="%.1f", step=0.5),
                    "반 평균": st.column_config.NumberColumn("반 평균", min_value=0.0, max_value=100.0, format="%.1f", step=0.5)
                }
            )
            
            q_labels, q_scores, q_avgs = [], [], []
            for _, row in edited_df.iterrows():
                q_labels.append(row["월"])
                if row["원생 점수"] > 0:
                    q_scores.append(row["원생 점수"])
                    q_avgs.append(row["반 평균"])
                else:
                    q_scores.append(None)
                    q_avgs.append(None)
            
            if not any(s is not None for s in q_scores):
                fallback_idx = allowed_months.index(eval_month_str) if eval_month_str in allowed_months else 0
                q_scores[fallback_idx] = float(student_score)
                q_avgs[fallback_idx] = float(class_avg)

            st.markdown("---")
            st.markdown(f"#### <span style='color:{RED};'>💡 선생님의 메모 (출력에 매우 중요)</span>", unsafe_allow_html=True)
            st.caption("원생의 특이사항을 적어주시면, 결과지의 가장 마지막 항목으로 정렬되어 출력됩니다.")
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
            subject=subject, next_subject=next_subject,
            metrics={"수업태도":m1,"과제수행":m2,"계산력(연산)":m3,
                     "심화문제풀이":m4,"학업성취도":m5},
            q_scores=[float(s) if s is not None else None for s in q_scores], q_avgs=[float(a) if a is not None else None for a in q_avgs], q_labels=q_labels,
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
            obs.append(f"{d['student_name']} 원생은 종합 평균에서 반 평균 대비 {diff:+.1f}점으로 우수한 성취를 기록했습니다.")
        elif diff>=0:
            obs.append(f"종합 평균 점수는 반 평균 대비 {diff:+.1f}점으로 안정적인 학습 성취를 유지하고 있습니다.")
        else:
            obs.append(f"종합 평균 점수가 반 평균보다 {diff:.1f}점 낮아 집중 보완이 필요한 상황입니다.")
        
        if strong:
            obs.append(f"5대 지표 중 {', '.join(strong)} 영역에서 90점 이상의 뛰어난 역량을 보이고 있습니다.")
        if weak:
            obs.append(f"반면 {', '.join(weak)} 영역은 보완이 필요하며, 관련 유형의 반복 훈련을 강화하고 있습니다.")

        qs=[s for s in d["q_scores"] if s is not None]
        if len(qs) >= 2:
            if qs[-1]>qs[-2]: obs.append(f"이전 평가 대비 {qs[-1]-qs[-2]:+.1f}점 향상된 흐름입니다.")
            elif qs[-1]<qs[-2]: obs.append(f"이전 평가 대비 하락하였으나, 개념 보완으로 회복 가능합니다.")
            else: obs.append("꾸준한 학습 흐름을 유지하고 있습니다.")
        
        p2=" ".join(obs)
        if d.get("exam_analysis"): p2 += f"\n\n[시험지 문항별 분석 결과]\n{d['exam_analysis']}"
        p3 = f"다음 달에는 '{d['next_subject']}' 과정에 대한 진도 학습 및 응용 훈련이 진행될 예정입니다."
        p4 = d['memo'] if d.get("memo") else ""

        return "\n\n".join([p for p in [p1, p2, p3, p4] if p.strip()])

    def gemini_ai_comment(d):
        try:
            genai.configure(api_key=d["gemini_key"])
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            metrics_str="\n".join(f"  - {k}: {v}점" for k,v in d["metrics"].items())
            exam_section = ""
            if d.get("exam_analysis"):
                exam_section = f"\n[시험지 문항별 분석 결과 — 반드시 2문단에 구체적으로 반영할 것]\n{d['exam_analysis']}\n"
            
            # [수정] 원생 데이터 명칭 반영
            content=[f"""당신은 수학 전문 학원 강사입니다. 학부모 상담용 리포트를 작성하십시오.

[원생 데이터]
- 이름: {d['student_name']}
- 이번 달 단원: {d['subject']}
- 다음 달 진도: {d['next_subject']}
- 평가 1회: 원생 {d['score1']}점 / 평균 {d['avg1']}점
- 평가 2회: 원생 {d['score2']}점 / 평균 {d['avg2']}점
- 종합 평균: 원생 {d['student_score']}점 / 평균 {d['class_avg']}점
- 5대 평가 지표:
{metrics_str}
- 강사 메모: {d['memo']}{exam_section}
[작성 규칙]
- 과도한 미사여구 없이 팩트 기반 교육 컨설턴트 톤 (~했습니다, ~할 예정입니다)
- 필수 4문단 구조 (각 문단은 엔터키로 명확히 구분):
  1문단: 이번 달 단원 핵심 개념 (3~4줄)
  2문단: 평가 결과 추이 및 지표 기반 정밀 관찰 (시험지 분석이 있을 경우 여기에 구체적 서술) (5~6줄)
  3문단: 다음 달 진도 계획 및 로드맵 (데이터의 '다음 달 진도' 바탕 작성) (2~3줄)
  4문단: 선생님의 관찰 메모 (데이터의 '강사 메모' 바탕 작성하되 제목 등은 절대 쓰지 말고 본문만 작성) (2~3줄)

순수 텍스트 4문단만 출력하십시오."""]

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
        fig.add_trace(go.Scatterpolar(r=[100]*len(cats)+[100], theta=cats_r, fill="toself", fillcolor="rgba(230,235,245,0.5)", line=dict(color="#D5DCE8",width=1), showlegend=False))
        fig.add_trace(go.Scatterpolar(r=vals_r, theta=cats_r, fill="toself", fillcolor="rgba(201,168,76,0.18)", line=dict(color=GOLD, width=2.5), marker=dict(size=9, color=GOLD, line=dict(width=2,color="white")), text=[f"<b>{v}점</b>" for v in vals]+[f"<b>{vals[0]}점</b>"], textposition="top center", mode="markers+lines+text", name=d["student_name"]))
        fig.update_layout(polar=dict(bgcolor="white", radialaxis=dict(visible=True, range=[0,100], tickvals=[25,50,75,100], tickfont=dict(size=9,color="#bbb"), gridcolor="#E8ECF2", linecolor="#E8ECF2"), angularaxis=dict(tickfont=dict(size=14,color=CHARCOAL), linecolor="#D5DCE8")), height=420, margin=dict(l=30,r=30,t=30,b=30), showlegend=False)
        return fig

    def make_trend(d):
        labels, scores, avgs = d["q_labels"], d["q_scores"], d["q_avgs"]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=labels, y=scores, name="원생 점수", marker_color=GOLD, text=[f"<b>{s:.1f}</b>" if s is not None else "" for s in scores], textposition="outside", textfont=dict(size=12, color=GOLD)))
        fig.add_trace(go.Bar(x=labels, y=avgs, name="반 평균", marker_color=SILVER, text=[f"{a:.1f}" if a is not None else "" for a in avgs], textposition="outside", textfont=dict(size=11, color=SILVER)))
        fig.update_layout(
            barmode='group',
            bargap=0.3,
            bargroupgap=0.15,
            height=300, margin=dict(l=55, r=20, t=50, b=60),
            paper_bgcolor="white", plot_bgcolor="white",
            yaxis=dict(range=[0, 120], showgrid=True, gridcolor="#F2F4F8"),
            xaxis=dict(type='category', categoryarray=labels),
            legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center")
        )
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
      {d['student_name']} 원생 성적표 미리보기
    </div>
    <div style="margin-top:7px;font-size:15px;color:{GOLD2};opacity:.9;">
      {d['student_grade']} | 담당: {d['teacher_name']}
    </div>
  </div>
  <div style="text-align:center;background:rgba(255,255,255,0.12);
              border-radius:12px;padding:14px 20px;border:1px solid {GOLD}55;margin-left:auto;">
    <div style="font-size:10px;color:{GOLD2};margin-bottom:4px;letter-spacing:1px;">월간 종합 등급</div>
    <div style="font-size:22px;font-weight:900;color:{GOLD};">{glv}</div>
  </div>
</div>""", unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    cards=[
        (c1, "평가 1회", d['score1'], d['avg1'], False),
        (c2, "평가 2회", d['score2'], d['avg2'], False),
        (c3, "월간 종합 평균", d['student_score'], d['class_avg'], True)
    ]
    for col, lbl, s_score, a_score, is_main in cards:
        with col:
            bg_color = "linear-gradient(135deg, #ffffff, #fdfbf7)" if not is_main else "linear-gradient(135deg, #fefdf9, #f4ecd8)"
            bd_color = f"{GOLD}66" if not is_main else GOLD
            lbl_bg   = f"{GOLD}22" if not is_main else GOLD
            lbl_clr  = CHARCOAL if not is_main else "white"
            st.markdown(f"""
            <div style="background:{bg_color}; border:2px solid {bd_color}; border-radius:12px; padding:12px;
                 text-align:center; box-shadow:0 4px 12px rgba(201,168,76,0.15); margin-bottom:5px; height:100%;">
              <div style="font-size:13px; font-weight:800; color:{lbl_clr}; margin-bottom:12px; background:{lbl_bg}; display:inline-block; padding:4px 14px; border-radius:20px;">{lbl}</div>
              <div style="display:flex; justify-content:space-around; align-items:center;">
                 <div style="text-align:center; flex:1;">
                   <div style="font-size:11px; color:#888; font-weight:600; margin-bottom:4px;">원생 점수</div>
                   <div style="font-size:24px; font-weight:900; color:#2C5282; font-family:'Noto Serif KR'">{s_score:.1f}<span style="font-size:13px;color:#aaa">점</span></div>
                 </div>
                 <div style="width:2px; height:35px; background:#ddd; margin:0 10px;"></div>
                 <div style="text-align:center; flex:1;">
                   <div style="font-size:11px; color:#888; font-weight:600; margin-bottom:4px;">반 평균</div>
                   <div style="font-size:20px; font-weight:700; color:{SILVER}; font-family:'Noto Serif KR'">{a_score:.1f}<span style="font-size:13px;color:#aaa">점</span></div>
                 </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("")
    col_r, col_t = st.columns([1,1], gap="large")
    with col_r:
        with st.container(border=True):
            st.markdown("#### 🕸️ 역량 방사형 분포")
            st.plotly_chart(make_radar(d),use_container_width=True, config={"displayModeBar":False, "staticPlot":True})
    with col_t:
        with st.container(border=True):
            st.markdown("#### 📈 월별 종합 성적 향상 추이")
            st.plotly_chart(make_trend(d),use_container_width=True, config={"displayModeBar":False, "staticPlot":True})

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
        st.markdown(f"#### 📝 월별 학습 진단 <span style='font-size:11px;color:#aaa'>({mode_lbl})</span>", unsafe_allow_html=True)
        paragraphs = [p for p in comment_text.split("\n\n") if p.strip()]
        labels = ["📘 단원 연계성", "🔍 이번 달 종합", "🗺️ 다음 달 로드맵", "📝 선생님의 메모"]
        preview_html = "<table style='width:100%; border-collapse:collapse;'>"
        for i, p_text in enumerate(paragraphs):
            lbl = labels[min(i, 3)]
            preview_html += f"<tr><td style='width:140px; padding:12px 10px 12px 0; vertical-align:top; font-weight:800; color:{CHARCOAL}; border-bottom:1px solid #E8ECF4;'>{lbl}</td><td style='padding:12px 0; vertical-align:top; line-height:1.7; color:#333; text-align:justify; border-bottom:1px solid #E8ECF4;'>{p_text.strip()}</td></tr>"
        preview_html += "</table>"
        st.markdown(preview_html, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # HTML 출력 (PDF 인쇄용)
    # ═══════════════════════════════════════════════════
    # ═══════════════════════════════════════════════════
    # HTML 출력 (PDF 인쇄용 및 이미지 생성용)
    # ═══════════════════════════════════════════════════
    def build_html(d, comment, for_image=False):
        W = 560
        # 이미지 캡처용일 경우 배경색과 레이아웃 소폭 조정
        body_bg = "#ffffff" if for_image else "#DDE2EC"
        page_margin = "0 auto" if for_image else "0 auto 20px"
        page_box_shadow = "none" if for_image else "0 4px 24px rgba(11,31,75,0.14)"
        
        def fw(fig, h): fig.update_layout(width=W, height=h, autosize=False, margin=dict(l=55, r=15, t=45, b=60), font=dict(size=10)); return fig
        radar_h = fw(make_radar(d), 360).to_html(full_html=False, include_plotlyjs="cdn", config={"displayModeBar":False, "staticPlot":True})
        trend_h = fw(make_trend(d), 240).to_html(full_html=False, include_plotlyjs=False, config={"displayModeBar":False, "staticPlot":True})
        glv,gcol = grade_info(d["student_score"])
        best_m = max(d["metrics"], key=d["metrics"].get); best_s = d["metrics"][best_m]
        logo_img_print_html = f'<img src="data:image/png;base64,{logo_base64}" style="height:45px;margin-right:15px;vertical-align:middle;border-radius:4px">' if logo_img_html else ""
        rows=""
        for lbl,val in d["metrics"].items():
            filled=int(val/100*20); bar="■"*filled+"□"*(20-filled); grd=("최우수" if val>=90 else "우수" if val>=80 else "양호" if val>=70 else "성장중"); gc=(GOLD if val>=90 else "#1F516A" if val>=80 else GREEN if val>=70 else SILVER)
            rows+=(f"<tr><td style='padding:9px 16px;font-weight:700;color:{CHARCOAL};width:130px'>{lbl}</td><td style='padding:9px 16px;font-size:11px;color:#aaa;letter-spacing:-0.5px;font-family:monospace'>{bar}</td><td style='padding:9px 16px;font-weight:900;color:{CHARCOAL};text-align:right;width:60px'>{val}점</td><td style='padding:9px 16px;text-align:right;width:90px'><span style='background:{gc}18;color:{gc};padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700'>{grd}</span></td></tr>")

        print_paragraphs = [p for p in comment.split("\n\n") if p.strip()]
        print_labels = ["📘 단원 연계성", "🔍 이번 달 종합", "🗺️ 다음 달 로드맵", "📝 선생님의 메모"]
        paras_html = "<table style='width:100%; border-collapse:collapse; margin-top:10px;'>"
        for i, p_text in enumerate(print_paragraphs):
            lbl = print_labels[min(i, 3)]
            paras_html += f"<tr><td style='width:130px; padding:14px 10px 14px 0; vertical-align:top; font-size:10.5pt; font-weight:800; color:{CHARCOAL}; border-bottom:1px solid #EEF1F8;'>{lbl}</td><td style='padding:14px 0; vertical-align:top; font-size:10.5pt; line-height:1.8; color:#333; text-align:justify; border-bottom:1px solid #EEF1F8;'>{p_text.strip()}</td></tr>"
        paras_html += "</table>"

        exam_section_html=f'<div style="margin:20px 0;padding:16px 20px;background:#FAFBFE;border-left:4px solid {GOLD};border-radius:0 8px 8px 0"><div style="font-size:11pt;font-weight:800;color:{CHARCOAL};margin-bottom:10px">📖 시험지 문항별 분석 결과</div><div style="font-size:10.5pt;line-height:1.9;color:#444;white-space:pre-wrap">{d["exam_analysis"]}</div></div>' if d.get("exam_analysis") else ""
        seal_svg=f'<svg width="88" height="88" viewBox="0 0 88 88" xmlns="http://www.w3.org/2000/svg"><circle cx="44" cy="44" r="42" fill="none" stroke="{GOLD}" stroke-width="2.5" stroke-dasharray="5 3"/><circle cx="44" cy="44" r="34" fill="none" stroke="{GOLD}" stroke-width="1.2"/><text x="44" y="36" text-anchor="middle" font-family="serif" font-size="9" fill="{GOLD}" font-weight="bold">{d["academy_name"][:4]}</text><text x="44" y="50" text-anchor="middle" font-family="serif" font-size="9" fill="{GOLD}" font-weight="bold">성적 확인</text><text x="44" y="62" text-anchor="middle" font-family="serif" font-size="8" fill="{GOLD}">CERTIFIED</text></svg>'

        # [수정] 출력용 HTML 내 모든 '학생' -> '원생' 일괄 적용
        return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet"><script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script><style>
*{{box-sizing:border-box;margin:0;padding:0}} body{{font-family:'Noto Sans KR',sans-serif;background:{body_bg};padding:20px}} @media print{{ body{{background:white!important;padding:0!important}} .no-print{{display:none!important}} @page{{size:A4 portrait;margin:12mm}} .page{{box-shadow:none!important;margin:0!important;border-radius:0!important;width:100%!important;min-height:auto!important;padding:0!important;border-top:4px solid {GOLD}!important;}} }}
.page{{width:210mm;min-height:296mm;background:white;margin:{page_margin};padding:10mm 14mm 20mm;box-shadow:{page_box_shadow};page-break-after:always;position:relative;border-top:5px solid {GOLD};}} .hdr{{background:linear-gradient(135deg,{CHARCOAL},{CHARCOAL2});color:white;border-radius:8px;padding:12px 18px;margin-bottom:12px;border-left:4px solid {GOLD};display:flex;justify-content:space-between;align-items:center;}}
.hdr-left .ac{{font-size:14pt;font-weight:800;color:{GOLD2};letter-spacing:1px;margin-bottom:4px}} .hdr-left .ti{{font-size:22pt;font-weight:900;font-family:'Noto Serif KR';margin-bottom:4px}} .hdr-left .sub{{font-size:12pt;color:{GOLD2};opacity:.9;margin-top:4px}} .hdr-grade{{text-align:center;background:rgba(255,255,255,0.12);border-radius:8px;padding:8px 14px;border:1px solid {GOLD}55;min-width:70px;flex-shrink:0;margin-left:12px}} .hdr-grade .gvl{{font-size:16pt;font-weight:900;color:{GOLD}}}
.sec{{font-size:10.5pt;font-weight:800;color:{CHARCOAL};border-left:3px solid {GOLD};padding-left:9px;font-family:'Noto Serif KR'}}
.srow{{display:flex;gap:12px;margin-top:35px;margin-bottom:50px;}}
.sbox{{flex:1;text-align:center;border-radius:12px;padding:12px 10px;border:2px solid {GOLD};background:#fff;box-shadow:0 6px 20px rgba(201,168,76,0.12);position:relative;}}
.sbox.main{{background:#FCFAF4; border:2.5px solid #AF8E36; box-shadow:0 8px 25px rgba(175,142,54,0.25); transform:translateY(-2px);}}
.sbox-title{{font-size:10pt;font-weight:800;color:{CHARCOAL};margin-bottom:12px;display:inline-block;background:rgba(201,168,76,0.15);padding:4px 14px;border-radius:20px; border:1px solid rgba(201,168,76,0.4);}}
.sbox.main .sbox-title{{background:#AF8E36; color:white; border-color:#AF8E36;}}
.sbox-content{{display:flex;justify-content:center;align-items:center; gap:8px;}}
.sbox-item{{flex:1;text-align:center;}}
.sbox-item .lbl{{font-size:8.5pt;color:#888;margin-bottom:4px;font-weight:600;}}
.sbox-item .val{{font-size:16pt;font-weight:900;color:#2C5282;font-family:'Noto Serif KR';}}
.sbox-item .avg{{font-size:13pt;color:{SILVER};}}
.sbox.main .sbox-item .val{{font-size:19pt;color:#1E3A8A;}}
.sbox-divider{{width:1.5px;height:35px;background:#eee;}}
table.mt{{width:100%;border-collapse:collapse;background:#FAFBFE;border:1px solid #E8ECF4}} table.mt td{{font-size:9.5pt;padding:7px 10px}} .ft{{position:absolute;bottom:6mm;left:14mm;right:14mm;display:flex;justify-content:space-between;border-top:1px solid {GOLD}44;padding-top:5px;font-size:8pt;color:#aaa}}
</style></head><body>
<div class="page"><div class="hdr"><div class="hdr-left" style="display:flex; align-items:center;">{logo_img_print_html}<div><div class="ac"><b>{d['academy_name']}</b> · {d['report_month']} 성적표</div><div class="ti">{d['student_name']} 원생 학업 성취 리포트</div><div class="sub">{d['student_grade']} | 담당: {d['teacher_name']}</div></div></div><div class="hdr-grade"><div style="font-size:8pt;color:{GOLD2}">종합 등급</div><div class="gvl">{glv}</div></div></div>
<div class="srow">
  <div class="sbox">
    <div class="sbox-title">평가 1회</div><div class="sbox-content"><div class="sbox-item"><div class="lbl">원생 점수</div><div class="val">{d['score1']:.1f}</div></div><div class="sbox-divider"></div><div class="sbox-item"><div class="lbl">반 평균</div><div class="val avg">{d['avg1']:.1f}</div></div></div>
  </div>
  <div class="sbox">
    <div class="sbox-title">평가 2회</div><div class="sbox-content"><div class="sbox-item"><div class="lbl">원생 점수</div><div class="val">{d['score2']:.1f}</div></div><div class="sbox-divider"></div><div class="sbox-item"><div class="lbl">반 평균</div><div class="val avg">{d['avg2']:.1f}</div></div></div>
  </div>
  <div class="sbox main">
    <div class="sbox-title">월간 종합 평균</div><div class="sbox-content"><div class="sbox-item"><div class="lbl">원생 종합</div><div class="val">{d['student_score']:.1f}</div></div><div class="sbox-divider"></div><div class="sbox-item"><div class="lbl">반 종합 평균</div><div class="val avg">{d['class_avg']:.1f}</div></div></div>
  </div>
</div>
<div class="sec" style="margin-bottom:20px;">🏷️ 5대 평가 지표 상세</div><table class="mt" style="margin-bottom:50px;">{rows}</table><div class="sec" style="margin-bottom:20px;">🕸️ 5대 영역별 역량 방사형 분포</div>{radar_h}<div class="ft"><span>{d['academy_name']}</span><span>1 / 2</span></div></div>
<div class="page">
<div class="hdr"><div class="hdr-left" style="display:flex; align-items:center;">{logo_img_print_html}<div><div class="ti" style="margin-bottom:0;">{d['student_name']} 원생 — 학습 진단 &amp; 로드맵</div></div></div></div>
<div class="sec" style="margin-top:25px; margin-bottom:20px;">📈 월별 성적 향상 추이</div><div style="margin-bottom:40px;">{trend_h}</div><div class="sec" style="margin-bottom:20px;">📝 월별 학습 진단</div>{paras_html}{exam_section_html}
<div style="display:flex;justify-content:flex-end;align-items:center;margin-top:40px;gap:16px"><div style="text-align:right"><div style="font-size:9pt;color:#888">담당 강사 확인</div><div style="font-size:11pt;font-weight:700;color:{CHARCOAL};border-bottom:1px solid {CHARCOAL};min-width:110px">{d['teacher_name']}</div></div>{seal_svg}</div>
<div class="ft"><span>{d['academy_name']} — 학원 공식 발행 문서</span><span>2 / 2</span></div></div></body></html>"""

    st.markdown("---")
    st.markdown(f"#### 📤 출력 옵션 설정")
    output_format = st.radio("다운로드 할 파일 형식을 선택하세요:", ["HTML 파일 (PC용)", "이미지 파일 (모바일용)", "둘 다 생성"], index=0, horizontal=True)
    st.markdown("")

    # 1. HTML 생성
    html_out = build_html(d, comment_text, for_image=False)
    b64_html = base64.b64encode(html_out.encode("utf-8")).decode()
    html_fname = f"성적표_{d['student_name']}_{d['report_month']}_{datetime.now().strftime('%m%d')}.html"
    
    # 2. 이미지 생성 (선택 시)
    show_html = output_format in ["HTML 파일 (PC용)", "둘 다 생성"]
    show_img  = output_format in ["이미지 파일 (모바일용)", "둘 다 생성"]
    
    col1, col2 = st.columns(2)
    
    if show_html:
        with col1:
            st.markdown(f'<a href="data:text/html;base64,{b64_html}" download="{html_fname}" style="display:block;background:{CHARCOAL};color:white;text-align:center;padding:15px;border-radius:12px;font-size:16px;font-weight:700;text-decoration:none;border-bottom:3px solid {GOLD}">📂 HTML 다운로드 (PC/인쇄용)</a>', unsafe_allow_html=True)
            st.caption("💡 Chrome/Safari로 열어 ⌘+P(인쇄) 후 PDF로 저장이 가능합니다.")

    if show_img:
        with col2:
            if st.button("🖼️ 이미지 파일 생성 및 다운로드", use_container_width=True, type="primary"):
                with st.spinner("🖼️ 고화질 이미지 생성 중... (약 5~10초 소요)"):
                    try:
                        from html2image import Html2Image
                        img_html = build_html(d, comment_text, for_image=True)
                        hti = Html2Image(custom_flags=['--no-sandbox', '--disable-gpu', '--hide-scrollbars'])
                        img_name = f"report_{d['student_name']}_{datetime.now().strftime('%H%M%S')}.png"
                        hti.screenshot(html_str=img_html, save_as=img_name, size=(850, 2400))
                        
                        if os.path.exists(img_name):
                            with open(img_name, "rb") as f:
                                st.download_button(
                                    label="⬇️ 생성 완료! 이미지 다운로드 클릭",
                                    data=f,
                                    file_name=f"성적표_{d['student_name']}_{d['report_month']}.png",
                                    mime="image/png",
                                    use_container_width=True
                                )
                            os.remove(img_name)
                    except Exception as e:
                        st.error(f"이미지 생성 중 오류가 발생했습니다: {e}")

