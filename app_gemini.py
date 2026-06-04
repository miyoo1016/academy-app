import streamlit as st
from datetime import datetime
import base64, io, os, re
# Heavy imports moved to functions or lazy loading to speed up initial 'Oven' time

# ═══════════════════════════════════════════════════════
# Google Sheets 연동 헬퍼
# ═══════════════════════════════════════════════════════
SHEET_COLS = [
    "created_at", "year", "teacher_name", "student_name", "grade",
    "eval_month", "test_name", "test_round", "score", "class_avg",
    "total_students", "rank", "weak_points", "ai_comment", "memo",
]

@st.cache_resource(show_spinner=False)
def get_gsheet():
    """Google Sheets 커넥션을 캐싱해서 반환. 인증 실패 시 None 반환."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(st.secrets["GOOGLE_SHEET_ID"])
        return sh.worksheet("scores")
    except Exception as e:
        st.warning(f"⚠️ Google Sheets 연결 실패: {e}")
        return None

def upgrade_sheet_if_needed(ws):
    """기존 시트에 year 컬럼이 없으면 A:O 스키마로 전체 마이그레이션 수행"""
    try:
        data = ws.get("A:O")
        if not data:
            return
        header = [str(c).strip() for c in data[0]]
        if "year" in header:
            return  # 이미 업그레이드 됨
            
        # 마이그레이션 진행
        new_rows = [SHEET_COLS]
        for raw_row in data[1:]:
            if len(raw_row) == 1 and "\t" in raw_row[0]:
                raw_row = raw_row[0].split("\t")
            padded = raw_row + [""] * (len(header) - len(raw_row))
            record = dict(zip(header, padded))
            
            row_year = str(record.get("year", "")).strip()
            if not row_year:
                created = str(record.get("created_at", "")).strip()
                if created and "-" in created:
                    row_year = created.split("-")[0]
                else:
                    try:
                        from zoneinfo import ZoneInfo
                        row_year = str(datetime.now(ZoneInfo("Asia/Seoul")).year)
                    except Exception:
                        row_year = str(datetime.now().year)
            record["year"] = row_year
            
            new_row = [str(record.get(col, "")) for col in SHEET_COLS]
            new_rows.append(new_row)
            
        ws.batch_clear(["A:O"])
        ws.update(new_rows, range_name="A1", value_input_option="USER_ENTERED")
    except Exception as e:
        print(f"Migration failed: {e}")

def save_to_sheet(d: dict, ai_comment: str) -> bool:
    """report_data dict -> scores 시트 A:O 범위에 저장. 중복 시 업데이트, 없으면 append. 실패 시 False 반환."""
    ws = get_gsheet()
    if ws is None:
        return False
    try:
        # 저장 전 스키마 확인
        data = ws.get("A1:O1")
        header = [str(c).strip() for c in data[0]] if data else []
        if header and "year" not in header:
            upgrade_sheet_if_needed(ws)

        metrics = d.get("metrics", {})
        weak_keys = [k for k, v in metrics.items() if v < 75]
        # 15개 컬럼 순서 고정 리스트 (SHEET_COLS 순서와 1:1 대응)
        try:
            from zoneinfo import ZoneInfo
            now_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        target_year = str(d.get("report_year", "")).strip()
        target_name = str(d.get("student_name", "")).strip().replace(" ", "")
        target_grade = normalize_grade_for_match(d.get("student_grade", ""))
        target_month = _parse_month(d.get("report_month", ""))
            
        row_values = [
            now_str,
            str(d.get("report_year", "")),
            str(d.get("teacher_name", "")),
            str(d.get("student_name", "")),
            str(d.get("student_grade", "")),
            str(d.get("report_month", "")),
            str(d.get("subject", "")),
            "",
            d.get("student_score", ""),
            d.get("class_avg", ""),
            "",
            "",
            ", ".join(weak_keys),
            str(ai_comment or "")[:500],
            str(d.get("memo", "")),
        ]
        
        # 전체 데이터를 가져와서 중복 검색 (가장 첫 번째 매칭 기준)
        all_data = ws.get("A:O")
        match_idx = -1
        if all_data and len(all_data) > 1:
            for i, raw_row in enumerate(all_data[1:]):
                if len(raw_row) == 1 and "\t" in raw_row[0]:
                    raw_row = raw_row[0].split("\t")
                padded = (raw_row + [""] * 15)[:15]
                
                row_year = str(padded[1]).strip()
                row_name = str(padded[3]).replace(" ", "").strip()
                row_grade = normalize_grade_for_match(padded[4])
                row_month = _parse_month(padded[5])
                
                if row_year == target_year and row_name == target_name and row_grade == target_grade and row_month == target_month:
                    match_idx = i + 2 # 헤더가 1행이므로 +2
                    break
                    
        if match_idx > 0:
            ws.update([row_values], range_name=f"A{match_idx}:O{match_idx}", value_input_option="USER_ENTERED")
        else:
            ws.append_row(
                row_values,
                value_input_option="USER_ENTERED",
                table_range="A1",
            )
            
        dedupe_scores_sheet(ws)
        sort_scores_sheet(ws)   # 저장 후 즉시 정렬
        return True
    except Exception as e:
        st.error(f"저장 실패: {e}")
        return False

def _parse_month(val: str) -> int:
    """eval_month 값을 정수 월로 변환. 파싱 실패 시 0 반환."""
    v = str(val).strip()
    # "2026-03" 형태
    if "-" in v:
        parts = v.split("-")
        for p in parts:
            try:
                n = int(p)
                if 1 <= n <= 12:
                    return n
            except ValueError:
                pass
    # "3월" / "03월" 형태
    v_num = v.replace("월", "").replace("월", "").strip()
    try:
        return int(v_num)
    except ValueError:
        return 0


def normalize_grade_for_match(raw) -> str:
    """학년 비교용 정규화. 원본 grade 저장값은 변경하지 않는다."""
    text = str(raw or "").strip().replace(" ", "")
    if not text:
        return ""

    compact = text.replace("초등학교", "초등").replace("초등", "초")
    compact = compact.replace("학년", "")
    match = re.fullmatch(r"초?([1-6])", compact)
    if match:
        return f"초등{match.group(1)}학년"

    middle = text.replace("중학교", "중").replace("중등", "중").replace("학년", "")
    match = re.fullmatch(r"중([1-3])", middle)
    if match:
        return f"중학교{match.group(1)}학년"

    return text.lower()


def dedupe_scores_sheet(ws) -> None:
    """scores 시트 A:O 범위에서 year+student_name+grade+eval_month 기준 중복이 있으면 created_at 최신 1건만 남김."""
    try:
        data = ws.get("A:O")
        if not data or len(data) < 2:
            return
            
        header = data[0]
        rows = data[1:]
        
        N = 15
        from collections import defaultdict
        groups = defaultdict(list)
        
        for r in rows:
            if any(str(c).strip() for c in r):
                if len(r) == 1 and "\t" in r[0]:
                    r = r[0].split("\t")
                padded = (r + [""] * N)[:N]
                
                # Composite key
                y = str(padded[1]).strip()
                name = str(padded[3]).replace(" ", "").strip()
                grade = normalize_grade_for_match(padded[4])
                month = _parse_month(padded[5])
                
                key = (y, name, grade, month)
                groups[key].append(padded)
                
        deduped_rows = []
        for key, group_rows in groups.items():
            if len(group_rows) == 1:
                deduped_rows.append(group_rows[0])
            else:
                # created_at (index 0) 기준 역순 정렬 (문자열 비교)
                group_rows.sort(key=lambda x: str(x[0]).strip(), reverse=True)
                deduped_rows.append(group_rows[0])
                
        if len(deduped_rows) < len(rows):
            # 중복이 있었다면 덮어쓰기
            last_row = 1 + max(len(rows), len(deduped_rows))
            if last_row >= 2:
                ws.batch_clear([f"A2:O{last_row}"])
                
            if deduped_rows:
                ws.update(
                    deduped_rows,
                    range_name=f"A2:O{1 + len(deduped_rows)}",
                    value_input_option="USER_ENTERED",
                )
    except Exception as e:
        print(f"Dedupe failed: {e}")

def sort_scores_sheet(ws) -> None:
    """scores 시트 A:O 범위의 2행 이하 데이터만 7단계 기준으로 정렬 후 A2부터 덮어씀."""
    try:
        data = ws.get("A:O")
        if not data or len(data) < 2:
            return
        header = data[0]
        rows = data[1:]

        # 각 행을 정확히 15컬럼으로 패딩/절단
        N = 15
        padded_rows = [
            (r + [""] * N)[:N]
            for r in rows
            if any(str(c).strip() for c in r)   # 완전 빈 행 제외
        ]

        # 컬럼 인덱스 (SHEET_COLS 순서)
        IDX = {col: i for i, col in enumerate(SHEET_COLS)}

        def sort_key(r):
            y = str(r[IDX["year"]]).strip()
            return (
                y,
                str(r[IDX["student_name"]]).strip().lower(),
                normalize_grade_for_match(r[IDX["grade"]]),
                _parse_month(r[IDX["eval_month"]]),
                str(r[IDX["test_name"]]).strip().lower(),
                int(str(r[IDX["test_round"]]).strip() or 0)
                if str(r[IDX["test_round"]]).strip().isdigit() else 0,
                str(r[IDX["created_at"]]).strip(),
            )

        padded_rows.sort(key=sort_key)

        # 기존 데이터 영역 클리어 (헤더 제외)
        last_row = 1 + max(len(data) - 1, len(padded_rows))
        if last_row >= 2:
            ws.batch_clear([f"A2:O{last_row}"])

        # 정렬된 데이터 A2부터 쓰기
        if padded_rows:
            ws.update(
                padded_rows,
                range_name=f"A2:O{1 + len(padded_rows)}",
                value_input_option="USER_ENTERED",
            )
    except Exception:
        pass   # 정렬 실패는 저장 성공에 영향 없음


def load_history(student_name: str, grade: str = "", year: str = "") -> list[dict]:
    """
    scores 시트 A:O에서 student_name (+grade) (+year) 필터링 후 행 반환.
    실패 시 빈 리스트 반환.
    """
    ws = get_gsheet()
    if ws is None:
        return []
    try:
        data = ws.get("A:O")
        if not data:
            return []
            
        header = [str(c).strip() for c in data[0]]
        if "year" not in header:
            upgrade_sheet_if_needed(ws)
            data = ws.get("A:O")
            
        if not data or len(data) < 2:
            return []
        
        name_clean  = student_name.replace(" ", "").strip()
        grade_clean = normalize_grade_for_match(grade)
        year_clean  = year.strip()
        result = []
        for raw_row in data[1:]:
            # 만약 시트 오류로 데이터가 한 셀에 탭(\t)으로 뭉쳐 들어온 경우 분리
            if len(raw_row) == 1 and "\t" in raw_row[0]:
                raw_row = raw_row[0].split("\t")
                
            padded = raw_row + [""] * (len(SHEET_COLS) - len(raw_row))
            record = dict(zip(SHEET_COLS, padded))
            
            row_name  = str(record.get("student_name", "")).replace(" ", "").strip()
            row_grade = normalize_grade_for_match(record.get("grade", ""))
            row_year  = str(record.get("year", "")).strip()
            
            # 이름 불일치면 건너뜀
            if row_name != name_clean:
                continue
            # grade가 주어졌고 둘 다 비어있지 않으면 학년도 일치해야 함
            if grade_clean and row_grade and row_grade != grade_clean:
                continue
            # 연도가 주어졌으면 연도도 일치해야 함
            if year_clean and row_year != year_clean:
                continue
                
            result.append(record)
            
        # 같은 eval_month 에 대해 created_at 최신 1건만 남김
        from collections import defaultdict
        month_map = defaultdict(list)
        for r in result:
            m = _parse_month(r.get("eval_month", ""))
            month_map[m].append(r)
            
        final_result = []
        for m, rows in month_map.items():
            if len(rows) == 1:
                final_result.append(rows[0])
            else:
                rows.sort(key=lambda x: str(x.get("created_at", "")).strip(), reverse=True)
                final_result.append(rows[0])
                
        return final_result
    except Exception:
        return []



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
    if score >= 90: return "최우수", GOLD
    if score >= 85: return "우수",   "#1A5276"
    if score >= 80: return "우수",   "#1A5276"
    if score >= 75: return "양호",   "#1B6B3A"
    if score >= 70: return "양호",   "#1B6B3A"
    return "성장중", "#5D7A8C"

# ═══════════════════════════════════════════════════════
# 로고 처리 로직 (image_0.png 파일 필수)
# ═══════════════════════════════════════════════════════
def get_base64_from_image(image_path_or_file):
    from PIL import Image
    buffered = io.BytesIO()
    if isinstance(image_path_or_file, str):
        with open(image_path_or_file, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    else:
        # PNG 형식으로 저장해도 JPEG 이미지를 처리할 수 있음 (PIL이 자동 변환)
        image_path_or_file.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

logo_path = 'image_0.png'
logo_img_html = ""
logo_base64 = ""

if os.path.exists(logo_path):
    try:
        from PIL import Image
        academy_logo_img = Image.open(logo_path)
        logo_base64 = get_base64_from_image(academy_logo_img)
        logo_img_html = f'<img src="data:image/png;base64,{logo_base64}" style="height:45px; margin-right:20px; vertical-align:middle; border-radius:6px; background-color:white; padding:4px; box-shadow: 0px 2px 5px rgba(0,0,0,0.2);">'
    except Exception as e:
        # Streamlit 로드 시 에러 발생 시 로그에 남김
        st.sidebar.error(f"Logo load error: {e}")

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
    
    try:
        from zoneinfo import ZoneInfo
        current_year = datetime.now(ZoneInfo("Asia/Seoul")).year
    except Exception:
        current_year = datetime.now().year
        
    START_YEAR = 2026
    allowed_years = [str(y) for y in range(START_YEAR, max(START_YEAR, current_year) + 2)]
    default_year = str(max(START_YEAR, current_year))
    default_index = allowed_years.index(default_year) if default_year in allowed_years else 0
    
    report_year   = st.selectbox("평가 연도", allowed_years, index=default_index)
    
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
    gemini_key = ""
    if "Gemini" in ai_mode:
        gemini_key = st.text_input("Google Gemini API Key", type="password", placeholder="AIza...")

    # --- [시스템 진단] ---
    with st.expander("🛠️ 시스템 진단 (Diagnostic)", expanded=False):
        st.write(f"📁 워킹 디렉토리: `{os.getcwd()}`")
        if os.path.exists(logo_path):
            st.success(f"✅ 로고 파일 확인: `{logo_path}`")
        else:
            st.warning(f"❌ 로고 파일 없음: `{logo_path}`")
        
        try:
            import pandas as pd
            st.write(f"📦 Pandas v{pd.__version__}")
        except: st.error("❌ Pandas 로드 실패")
        
        if st.button("시스템 리프레시 (Rerun)"):
            st.rerun()

# ═══════════════════════════════════════════════════════
# 헤더
# ═══════════════════════════════════════════════════════
st.markdown(f"""
<div style="background:linear-gradient(135deg,{CHARCOAL},{CHARCOAL2});border-radius:16px;
     padding:20px 28px;margin-bottom:20px;
     border-bottom:4px solid {GOLD}; display:flex; align-items:center;">
  {logo_img_html}
  <span style="font-size:26px;font-weight:900;color:white;font-family:'Noto Serif KR'">
    📊 학원 성적표 v2.2.0 (Premium)
  </span>
  <span style="font-size:14px;color:{GOLD2};margin-left:auto;">{academy_name}</span>
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# 내비게이션 제어 (상태 기반 탭 구현)
# ═══════════════════════════════════════════════════════
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = 0

# 탭 스타일링을 위한 헬퍼
tab_labels = ["✏️ 성적 입력", "📋 성적표 미리보기 & 출력"]

# 상단 탭 선택 바 (라디오 버튼을 탭처럼 스타일링하거나 기본 탭 사용 대신 세션 상태와 연동)
# 실제 st.tabs는 프로그램 제어가 어려우므로, 상태 기반으로 직접 렌더링 방식 선택 가능
# 여기서는 사용자 경험 유지를 위해 st.tabs를 쓰되, 단계 전환 버튼이 작동하도록 함

active_tab = st.session_state["active_tab"]

# 실제 탭 생성 (탭 이름을 세션 상태에 따라 동적으로 처리하거나, 직접 세션 상태로 분기)
# 가장 깔끔한 방법은 세션 상태에 따라 탭 중 하나가 '활성화'된 것처럼 보이게 하는 것이나
# Streamlit의 st.tabs는 현재 프로그래밍 방식의 인덱스 지정을 직접 지원하지 않습니다.
# 대신, 성적표 생성 시 자동으로 다음 단계를 보여주는 로직과 '수정' 버튼 클릭 시 
# 다시 입력 화면을 보여주는 로직을 위해 '전체 컨테이너 분기' 방식으로 전환합니다.

# 탭 UI를 세션 상태로 제어하기 위해 탭 대신 '라디오' 또는 '버튼' 기반 내비게이션 사용
st.markdown("""
<style>
    div[data-testid="stHorizontalBlock"] > div:has(button) { display: flex; justify-content: center; }
</style>
""", unsafe_allow_html=True)

nav_col1, nav_col2 = st.columns(2)
with nav_col1:
    if st.button("✏️ 성적 입력", use_container_width=True, type="primary" if st.session_state["active_tab"] == 0 else "secondary"):
        st.session_state["active_tab"] = 0
        st.rerun()
with nav_col2:
    if st.button("📋 성적표 미리보기 & 출력", use_container_width=True, type="primary" if st.session_state["active_tab"] == 1 else "secondary"):
        if "report_data" in st.session_state:
            st.session_state["active_tab"] = 1
            st.rerun()
        else:
            st.warning("먼저 성적을 입력하고 '성적표 생성하기'를 눌러주세요.")

st.markdown("---")

# ═══════════════════════════════════════════════════════
# 화면 분기 시작
# ═══════════════════════════════════════════════════════
if st.session_state["active_tab"] == 0:
    # --- [성적 입력 화면] ---
    with st.container(border=True):
        st.markdown(f"### 📎 시험지 업로드 <span style='font-size:13px;color:{GOLD};'>(Gemini AI 모드에서 문항별 분석 자동 반영)</span>", unsafe_allow_html=True)
        st.caption("JPG · PNG · PDF 지원 | 여러 장 동시 업로드 가능 | 파일 없이 수동 입력만으로도 생성 가능")
        uploaded_files = st.file_uploader("파일 선택", type=["jpg","jpeg","png","pdf"], accept_multiple_files=True, label_visibility="collapsed")
        if uploaded_files:
            cols = st.columns(min(len(uploaded_files),5))
            for i,f in enumerate(uploaded_files):
                if f.type.startswith("image"):
                    cols[i%5].image(f, caption=f.name, width="stretch")
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

            # ── Google Sheets 과거 성적 로드 ─────────────────────────────────────────
            # 원생 이름 또는 학년, 연도가 바뀌면 캐시 무효화 후 재조회
            _cache_key = f"{student_name}||{student_grade}||{report_year}"
            if st.session_state.get("_history_key") != _cache_key:
                st.session_state["_history_key"] = _cache_key
                st.session_state["_history_rows"] = load_history(student_name, student_grade, report_year)

            history_rows = st.session_state.get("_history_rows", [])

            # 월별 매핑: _parse_month로 정규화 후 allowed_months 레이블 기준으로 변환
            # allowed_months 각 레이블의 숫자 월을 미리 추출해두었다가 매핑
            _month_label_map = {_parse_month(m): m for m in allowed_months}  # {3: "3월", 4: "4월", ...}
            history_map: dict[str, tuple[float, float]] = {}
            for hr in history_rows:
                raw_month = str(hr.get("eval_month", "")).strip()
                m_num = _parse_month(raw_month)          # 숫자 월로 정규화
                m_label = _month_label_map.get(m_num)   # ex) 3 -> "3월"
                if not m_label:
                    continue                              # allowed_months에 없는 월 무시
                try:
                    s = float(hr.get("score", 0) or 0)
                    a = float(hr.get("class_avg", 0) or 0)
                    if s > 0:
                        # 같은 월에 여러 기록 있으면 가장 작성 날짜(created_at) 기준 최신 값 사용
                        if m_label not in history_map:
                            history_map[m_label] = (s, a)
                        else:
                            existing_ts = max(
                                str(x.get("created_at", ""))
                                for x in history_rows
                                if _parse_month(str(x.get("eval_month", ""))) == m_num
                            )
                            new_ts = str(hr.get("created_at", ""))
                            if new_ts >= existing_ts:
                                history_map[m_label] = (s, a)
                except (ValueError, TypeError):
                    pass

            trend_data = []
            for m_label in allowed_months:
                if m_label == eval_month_str:
                    # 이번 달: 현재 입력값 우선 (사용자가 수정 중인 값을 덮어쓰지 않음)
                    trend_data.append({
                        "월": m_label,
                        "원생 점수": float(student_score),
                        "반 평균": float(class_avg),
                    })
                elif m_label in history_map:
                    # 과거 달: Sheets 저장값 자동 반영
                    h_score, h_avg = history_map[m_label]
                    trend_data.append({"월": m_label, "원생 점수": h_score, "반 평균": h_avg})
                else:
                    trend_data.append({"월": m_label, "원생 점수": 0.0, "반 평균": 0.0})

            if history_map:
                loaded_months = sorted(history_map.keys(),
                                       key=lambda m: _parse_month(m))
                st.caption(
                    f"📂 과거 데이터 자동 반영: {', '.join(loaded_months)} ({len(history_map)}개월)"
                )

            import pandas as pd
            df_trend = pd.DataFrame(trend_data)

            import hashlib
            trend_hash = hashlib.md5(str(trend_data).encode()).hexdigest()
            # key에 캐시키+history 크기+데이터해시를 포함 → 원생/학년/데이터 변경 시 Streamlit이 위젯 강제 재생성
            _editor_key = f"trend__{_cache_key}__{len(history_map)}__{trend_hash}"
            edited_df = st.data_editor(
                df_trend,
                hide_index=True,
                width="stretch",
                key=_editor_key,
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
    gen_btn = st.button("🚀 성적표 생성하기", width="stretch", type="primary")

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
                        import google.generativeai as genai
                        from PIL import Image
                        genai.configure(api_key=gemini_key)
                        model = genai.GenerativeModel('gemini-2.0-flash')
                        
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
            report_year=report_year, report_month=report_month,
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
        st.session_state["active_tab"] = 1
        st.success("✅ 완료! 상단의 '📋 성적표 미리보기 & 출력' 버튼을 클릭하거나 자동으로 이동합니다.")
        st.rerun()

# ═══════════════════════════════════════════════════════
# 2. 미리보기 화면
# ═══════════════════════════════════════════════════════
else:
    if "report_data" not in st.session_state:
        st.info("✏️ '성적 입력' 단계에서 데이터를 입력하고 '성적표 생성하기'를 눌러주세요.")
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
            import google.generativeai as genai
            from PIL import Image
            genai.configure(api_key=d["gemini_key"])
            model = genai.GenerativeModel('gemini-2.0-flash')
            
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
        import plotly.graph_objects as go
        cats = list(d["metrics"].keys())
        vals = list(d["metrics"].values())
        cats_r=cats+[cats[0]]; vals_r=vals+[vals[0]]
        fig=go.Figure()
        fig.add_trace(go.Scatterpolar(r=[100]*len(cats)+[100], theta=cats_r, fill="toself", fillcolor="rgba(230,235,245,0.5)", line=dict(color="#D5DCE8",width=1), showlegend=False))
        fig.add_trace(go.Scatterpolar(r=vals_r, theta=cats_r, fill="toself", fillcolor="rgba(201,168,76,0.18)", line=dict(color=GOLD, width=2.5), marker=dict(size=9, color=GOLD, line=dict(width=2,color="white")), text=[f"<b>{v}점</b>" for v in vals]+[f"<b>{vals[0]}점</b>"], textposition="top center", mode="markers+lines+text", name=d["student_name"]))
        fig.update_layout(
            polar=dict(
                bgcolor="white",
                radialaxis=dict(visible=True, range=[0,100], tickvals=[25,50,75,100], tickfont=dict(size=9,color="#bbb"), gridcolor="#E8ECF2", linecolor="#E8ECF2"),
                angularaxis=dict(tickfont=dict(size=14,color=CHARCOAL), linecolor="#D5DCE8")
            ),
            height=420, margin=dict(l=30,r=30,t=30,b=30),
            showlegend=False,
            font=dict(family="NanumGothic, sans-serif")
        )
        return fig

    def make_trend(d):
        import plotly.graph_objects as go
        labels, scores, avgs = d["q_labels"], d["q_scores"], d["q_avgs"]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=labels, y=scores, name="원생 점수", marker_color=GOLD, text=[f"<b>{s:.1f}</b>" if s is not None else "" for s in scores], textposition="outside", textfont=dict(size=12, color=GOLD), cliponaxis=False))
        fig.add_trace(go.Bar(x=labels, y=avgs, name="반 평균", marker_color=SILVER, text=[f"{a:.1f}" if a is not None else "" for a in avgs], textposition="outside", textfont=dict(size=11, color=SILVER), cliponaxis=False))
        fig.update_layout(
            barmode='group',
            bargap=0.3,
            bargroupgap=0.15,
            height=300, margin=dict(l=55, r=20, t=50, b=60),
            paper_bgcolor="white", plot_bgcolor="white",
            yaxis=dict(range=[0, 115], showgrid=True, gridcolor="#F2F4F8"),
            xaxis=dict(type='category', categoryarray=labels),
            legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
            font=dict(family="NanumGothic, sans-serif")
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
            st.plotly_chart(make_radar(d),width="stretch", config={"displayModeBar":False, "staticPlot":True})
    with col_t:
        with st.container(border=True):
            st.markdown("#### 📈 월별 종합 성적 향상 추이")
            st.plotly_chart(make_trend(d),width="stretch", config={"displayModeBar":False, "staticPlot":True})

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

        # [수정] 출력용 HTML 내 모든 '학생' -> '원생' 일괄 적용 및 디자인 입히기
        return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet"><script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script><style>
*{{box-sizing:border-box;margin:0;padding:0}} body{{font-family:'Noto Sans KR',sans-serif;background:{body_bg};padding:20px}} @media print{{ body{{background:white!important;padding:0!important}} .no-print{{display:none!important}} @page{{size:A4 portrait;margin:12mm}} .page{{box-shadow:none!important;margin:0!important;border-radius:0!important;width:100%!important;min-height:auto!important;padding:0!important;border-top:4px solid {GOLD}!important;}} }}
.page{{
    width:210mm;min-height:296mm;background:white;margin:{page_margin};padding:10mm 14mm 20mm;
    box-shadow:{page_box_shadow};page-break-after:always;position:relative;
    border-top:8.0px solid {GOLD};
    background-image: radial-gradient(circle at 50% 50%, rgba(201,168,76,0.06) 0%, rgba(255,255,255,0) 70%);
    z-index: 1;
}}
.page::before {{
    content: "";
    position: absolute;
    top: 25%; left: 15%; right: 15%; bottom: 25%;
    background-image: url('data:image/svg+xml;utf8,<svg width="100%" height="100%" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"><circle cx="100" cy="100" r="80" fill="none" stroke="%23C9A84C" stroke-width="1.5" stroke-dasharray="4 4" opacity="0.1"/><text x="100" y="105" text-anchor="middle" font-family="serif" font-size="22" fill="%23C9A84C" font-weight="bold" opacity="0.15">미래학원 PRESTIGE</text></svg>');
    background-repeat: no-repeat;
    background-position: center;
    z-index: -1;
    pointer-events: none;
}}
.hdr{{
    background:linear-gradient(135deg,{CHARCOAL},{CHARCOAL2});
    color:white;border-radius:8px;padding:16px 22px;margin-bottom:15px;
    border-left:5px solid {GOLD};
    border-right:1px solid rgba(201,168,76,0.3);
    border-bottom:1px solid rgba(201,168,76,0.3);
    border-top:1px solid rgba(201,168,76,0.3);
    display:flex;justify-content:space-between;align-items:center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}}
.hdr-left .ac{{font-size:14pt;font-weight:800;color:{GOLD2};letter-spacing:1px;margin-bottom:4px}} .hdr-left .ti{{font-size:24pt;font-weight:900;font-family:'Noto Serif KR';margin-bottom:4px;text-shadow: 1px 1px 2px rgba(0,0,0,0.5);}} .hdr-left .sub{{font-size:12pt;color:{GOLD2};opacity:.9;margin-top:4px}} .hdr-grade{{text-align:center;background:rgba(201,168,76,0.15);border-radius:8px;padding:10px 16px;border:1px solid {GOLD};min-width:70px;flex-shrink:0;margin-left:12px}} .hdr-grade .gvl{{font-size:18pt;font-weight:900;color:{GOLD2};text-shadow: 0px 0px 4px rgba(201,168,76,0.6);}}
.sec{{font-size:11.5pt;font-weight:800;color:{CHARCOAL};border-left:4px solid {GOLD};padding-left:10px;font-family:'Noto Serif KR'; background: linear-gradient(90deg, rgba(201,168,76,0.15) 0%, transparent 100%); padding-top:5px; padding-bottom:5px; border-radius:2px;}}
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
    st.markdown("#### ⚙️ 리포트 관리 및 출력 설정")
    
    col_mod, col_home = st.columns(2)
    with col_mod:
        if st.button("✏️ 정보 수정하기 (입력 단계로)", use_container_width=True):
            st.session_state["active_tab"] = 0
            st.rerun()
    with col_home:
        if st.button("🏠 처음으로 (모든 데이터 초기화)", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # ── Google Sheets 저장 버튼 ─────────────────────────────────
    st.markdown("")
    with st.container(border=True):
        st.markdown(f"#### 💾 Google Sheets에 성적 저장")
        st.caption("저장하면 같은 원생 이름으로 다음 달 성적 입력 시 월별 추이에 자동 반영됩니다.")
        save_col, info_col = st.columns([1, 2])
        with save_col:
            if st.button("📊 Google Sheets에 저장", use_container_width=True, type="primary"):
                with st.spinner("저장 중..."):
                    ok = save_to_sheet(d, comment_text)
                if ok:
                    st.success(f"✅ {d['student_name']} 원생 {d['report_month']} 성적이 저장되었습니다!")
                    # 히스토리 캐시 무효화 → 다음 입력 탭 로드 시 최신 데이터 반영
                    st.session_state.pop("_history_key", None)
                    st.session_state.pop("_history_rows", None)
        with info_col:
            st.info(
                f"저장 대상: **{d['student_name']}** | {d['report_month']} | "
                f"점수 {d['student_score']:.1f}점 | 반평균 {d['class_avg']:.1f}점"
            )
    # ────────────────────────────────────────────────────────────

    st.markdown("")
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
            if st.button("🖼️ 이미지 파일 생성 및 다운로드", width="stretch", type="primary"):
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
                                    width="stretch"
                                )
                            os.remove(img_name)
                    except Exception as e:
                        st.error(f"이미지 생성 중 오류가 발생했습니다: {e}")

    # ═══════════════════════════════════════════════════
    # 3. 하단 컨트롤 버튼 (수정 및 처음으로)
    # ═══════════════════════════════════════════════════
    # st.markdown("---") # 위쪽에서 이미 선을 그음
    # (하단 중복 버튼 제거됨)
    st.markdown("<br><br>", unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
