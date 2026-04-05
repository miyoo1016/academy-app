#!/bin/bash
# ═══════════════════════════════════════════════════════
# 학원 성적표 v2 - 원클릭 실행
# 더블클릭으로 프로그램을 실행할 수 있습니다.
# ═══════════════════════════════════════════════════════

# 스크립트가 위치한 디렉토리로 이동
cd "$(dirname "$0")"

echo "============================================"
echo "  🏫 학원 성적표 v2 시작 중..."
echo "============================================"
echo ""

# 가상환경 활성화 (.venv 또는 venv)
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️  가상환경이 없습니다. 시스템 Python으로 실행합니다."
fi

# streamlit 설치 확인
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "📦 필요한 패키지를 설치합니다..."
    pip install -r requirements.txt
fi

echo "🚀 브라우저가 자동으로 열립니다..."
echo "   종료: 이 터미널 창을 닫으세요."
echo ""

# Streamlit 실행
python3 -m streamlit run app.py --server.headless false
