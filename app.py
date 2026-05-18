import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

st.set_page_config(page_title="코스피 비교 대시보드", layout="wide")
st.title("📈 코스피 상위 100종목 vs 코스피 지수 비교 분석")

today = datetime.today().strftime("%Y-%m-%d")
st.caption(f"📅 데이터 기준: {today}")

# ==================== 데이터 로드 ====================
@st.cache_data(ttl=3600)
def load_kospi_stocks():
    return fdr.StockListing('KOSPI')

df = load_kospi_stocks()
top100 = df.head(100).copy()

top100['시가총액(억)'] = (top100['Marcap'] / 100000000).round(0).astype(int)
top100['현재가'] = top100['Close'].apply(lambda x: f"{int(x):,}")
top100['하루변동률'] = top100['ChagesRatio'].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "0.00%")

# ==================== 검색창 ====================
st.subheader("🔍 종목 검색")
search = st.text_input("종목명 또는 종목코드로 검색하세요", placeholder="예: 삼성전자, 005930")

# 검색 필터링
if search:
    mask = (top100['Name'].str.contains(search, case=False)) | \
           (top100['Code'].str.contains(search, case=False))
    filtered = top100[mask].copy()
else:
    filtered = top100.copy()

# 시가총액 기준 정렬
filtered = filtered.sort_values(by='시가총액(억)', ascending=False).reset_index(drop=True)
filtered.insert(0, '순위', range(1, len(filtered)+1))

# ==================== 테이블 ====================
st.subheader(f"📋 검색 결과 ({len(filtered)}개)")

display_cols = ['순위', 'Code', 'Name', '현재가', '하루변동률', 'Volume', '시가총액(억)']

def color_change(val):
    if isinstance(val, str) and val.startswith('+'):
        return 'color: #00C853; font-weight: bold;'
    elif isinstance(val, str) and val.startswith('-'):
        return 'color: #FF5252; font-weight: bold;'
    return ''

styled_df = filtered[display_cols].style.map(
    color_change, subset=['하루변동률']
).set_properties(**{'text-align': 'right'}, 
                 subset=['현재가', '하루변동률', 'Volume', '시가총액(억)'])

st.dataframe(
    styled_df,
    use_container_width=True,
    height=600,
    hide_index=True,
    column_config={
        "순위": st.column_config.NumberColumn("순위", width=50),
        "Code": st.column_config.TextColumn("종목코드", width=80),
        "Name": st.column_config.TextColumn("종목명", width=180),
        "현재가": st.column_config.TextColumn("현재가", width=120),
        "하루변동률": st.column_config.TextColumn("하루 변동률", width=110),
        "Volume": st.column_config.NumberColumn("거래량", format="%,d", width=130),
        "시가총액(억)": st.column_config.NumberColumn("시가총액(억)", format="%,d", width=150)
    }
)

# ==================== 종목 비교 ====================
st.subheader("🔍 종목 vs 코스피 지수 비교")

col1, col2 = st.columns([1, 2])

with col1:
    selected_name = st.selectbox(
        "비교할 종목 선택",
        options=filtered['Name'].tolist(),   # 검색 결과에서 선택
        index=0 if len(filtered) > 0 else 0
    )
    ticker = filtered[filtered['Name'] == selected_name]['Code'].iloc[0]

with col2:
    period = st.radio(
        "기간 선택", 
        ["1일", "1개월", "3개월", "6개월", "1년"], 
        horizontal=True,
        index=1
    )

# (이하 비교 차트 부분은 이전과 동일)
days = {"1일": 1, "1개월": 30, "3개월": 90, "6개월": 180, "1년": 365}
start_date = (datetime.today() - timedelta(days=days[period])).strftime("%Y-%m-%d")

try:
    stock_data = fdr.DataReader(ticker, start=start_date)
    kospi_data = fdr.DataReader('KS11', start=start_date)
    
    stock_norm = (stock_data['Close'] / stock_data['Close'].iloc[0] * 100).round(2)
    kospi_norm = (kospi_data['Close'] / kospi_data['Close'].iloc[0] * 100).round(2)
    
    compare_df = pd.DataFrame({selected_name: stock_norm, '코스피 지수': kospi_norm})
    
    fig = px.line(compare_df, x=compare_df.index, y=[selected_name, '코스피 지수'],
                  color_discrete_sequence=['#FF4B4B', '#1E88E5'])
    fig.update_traces(line=dict(width=3.5))
    st.plotly_chart(fig, use_container_width=True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric(f"📈 {selected_name}", f"{(stock_norm.iloc[-1] - 100):+.2f}%")
    with col_b:
        st.metric("📊 코스피 지수", f"{(kospi_norm.iloc[-1] - 100):+.2f}%")

except Exception as e:
    st.error(f"데이터 오류: {e}")

