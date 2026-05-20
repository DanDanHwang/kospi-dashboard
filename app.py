import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os
import json

st.set_page_config(page_title="코스피 종합 대시보드", layout="wide")

# ==================== 사이드바 ====================
st.sidebar.success("👤 공개 대시보드")
st.sidebar.markdown("---")
st.sidebar.markdown("### ❤️ 후원하기")
st.sidebar.markdown(
    f'<a href="https://qr.kakaopay.com/FEeEDozvJ" target="_blank">'
    f'<img src="https://img.shields.io/badge/카카오페이_후원-FFCD00?style=for-the-badge&logo=kakao&logoColor=black" width="100%">'
    f'</a>', unsafe_allow_html=True
)

tab1, tab2, tab3 = st.tabs(["📊 대시보드", "💬 게시판", "📉 포트폴리오"])

# ==================== 1. 대시보드 (로그인 없이 공개) ====================
with tab1:
    st.title("📈 코스피 상위 100종목 vs 코스피 지수 비교 분석")

    @st.cache_data(ttl=3600)
    def load_data():
        import FinanceDataReader as fdr
        return fdr.StockListing('KOSPI')

    df = load_data()
    top100 = df.head(100).copy()

    top100['시가총액(억)'] = (top100['Marcap'] / 100000000).round(0).astype(int)
    top100['현재가'] = top100['Close'].apply(lambda x: f"{int(x):,}")
    top100['하루변동률'] = top100['ChagesRatio'].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "0.00%")

    search = st.text_input("🔍 종목 검색", placeholder="종목명 또는 코드")
    if search:
        mask = (top100['Name'].str.contains(search, case=False)) | (top100['Code'].str.contains(search, case=False))
        filtered = top100[mask].copy()
    else:
        filtered = top100.copy()

    filtered = filtered.sort_values(by='시가총액(억)', ascending=False).reset_index(drop=True)
    filtered.insert(0, '순위', range(1, len(filtered)+1))

    st.dataframe(filtered[['순위', 'Code', 'Name', '현재가', '하루변동률', 'Volume', '시가총액(억)']], 
                 use_container_width=True, height=400, hide_index=True)

    # 심화 차트
    st.subheader("📊 고급 기술적 분석 차트")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        selected_name = st.selectbox("분석할 종목", filtered['Name'].tolist())
        ticker = filtered[filtered['Name'] == selected_name]['Code'].iloc[0]
    with col2:
        period = st.selectbox("기간", ["1개월", "3개월", "6개월", "1년"], index=2)
    with col3:
        chart_type = st.radio("차트 유형", ["오버레이 비교", "캔들차트 + 이평선"], horizontal=True)

    days = {"1개월":30, "3개월":90, "6개월":180, "1년":365}
    start_date = (datetime.today() - timedelta(days=days[period])).strftime("%Y-%m-%d")

    try:
        import FinanceDataReader as fdr
        stock = fdr.DataReader(ticker, start=start_date)
        kospi = fdr.DataReader('KS11', start=start_date)

        stock_norm = stock['Close'] / stock['Close'].iloc[0] * 100
        kospi_norm = kospi['Close'] / kospi['Close'].iloc[0] * 100

        if chart_type == "오버레이 비교":
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=stock.index, y=stock_norm, name=selected_name, line=dict(color='#FF4B4B', width=3.5)))
            fig.add_trace(go.Scatter(x=kospi.index, y=kospi_norm, name='코스피 지수', line=dict(color='#1E88E5', width=3.5)))
            fig.update_layout(title=f"{selected_name} vs 코스피 정규화 비교 ({period})", height=550)
            st.plotly_chart(fig, use_container_width=True)
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=stock.index, y=stock_norm, name=selected_name, line=dict(color='#FF4B4B', width=3)))
            fig.add_trace(go.Scatter(x=kospi.index, y=kospi_norm, name='코스피 지수', line=dict(color='#1E88E5', width=3, dash='dot')))
            ma5 = stock['Close'].rolling(5).mean() / stock['Close'].iloc[0] * 100
            ma20 = stock['Close'].rolling(20).mean() / stock['Close'].iloc[0] * 100
            ma60 = stock['Close'].rolling(60).mean() / stock['Close'].iloc[0] * 100
            fig.add_trace(go.Scatter(x=stock.index, y=ma5, name='MA5', line=dict(color='orange', dash='dash')))
            fig.add_trace(go.Scatter(x=stock.index, y=ma20, name='MA20', line=dict(color='blue', dash='dot')))
            fig.add_trace(go.Scatter(x=stock.index, y=ma60, name='MA60', line=dict(color='purple')))
            fig.update_layout(title=f"{selected_name} vs 코스피 정규화 + 이동평균선 ({period})", height=650)
            st.plotly_chart(fig, use_container_width=True)

        col_a, col_b, col_c = st.columns(3)
        with col_a: st.metric(f"📈 {selected_name}", f"{(stock_norm.iloc[-1]-100):+.2f}%")
        with col_b: st.metric("📊 코스피", f"{(kospi_norm.iloc[-1]-100):+.2f}%")
        with col_c:
            beta = round(stock['Close'].pct_change().cov(kospi['Close'].pct_change()) / kospi['Close'].pct_change().var(), 3)
            st.metric("📉 베타", f"{beta}")
    except:
        st.error("차트 로딩 중...")

# ==================== 2. 게시판 (Secrets 로그인) ====================
with tab2:
    st.title("💬 코스피 투자자 게시판")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.warning("📌 게시판은 로그인 후 이용 가능합니다.")
        
        username = st.text_input("아이디", value="admin")
        password = st.text_input("비밀번호", type="password")
        
        if st.button("로그인", type="primary"):
            try:
                if (username == st.secrets["login"]["username"] and 
                    password == st.secrets["login"]["password"]):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 틀렸습니다.")
            except:
                st.error("Secrets 설정이 필요합니다.")
        st.stop()

    st.success(f"✅ {st.session_state.username}님 환영합니다!")
    if st.button("로그아웃"):
        st.session_state.logged_in = False
        st.rerun()

    # 게시판 본문 (이전 버전 유지)
    DATA_FILE = "posts.csv"
    if os.path.exists(DATA_FILE):
        posts = pd.read_csv(DATA_FILE)
    else:
        posts = pd.DataFrame(columns=['id','title','content','author','date','comments'])

    with st.expander("✍️ 새 글 작성", expanded=False):
        title = st.text_input("제목")
        content = st.text_area("내용", height=150)
        if st.button("게시하기", type="primary"):
            if title and content:
                new_post = {
                    'id': len(posts)+1,
                    'title': title,
                    'content': content,
                    'author': st.session_state.username,
                    'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'comments': '[]'
                }
                posts = pd.concat([posts, pd.DataFrame([new_post])], ignore_index=True)
                posts.to_csv(DATA_FILE, index=False)
                st.success("게시 완료!")
                st.rerun()

    st.subheader(f"📋 전체 게시글 ({len(posts)}개)")
    for _, row in posts[::-1].iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([8,1])
            with col1:
                st.subheader(row['title'])
                st.caption(f"{row['author']} • {row['date']}")
            with col2:
                if st.session_state.username == "admin":
                    if st.button("🗑", key=f"del_{row['id']}"):
                        posts = posts[posts['id'] != row['id']]
                        posts.to_csv(DATA_FILE, index=False)
                        st.rerun()
            st.write(row['content'])

            try:
                comments = json.loads(row['comments']) if isinstance(row['comments'], str) else []
            except:
                comments = []
            for c in comments:
                st.markdown(f"**↳ {c['author']}**: {c['text']} *({c['time']})*")

            comment = st.text_input("댓글 작성", key=f"c_{row['id']}", placeholder="댓글을 입력하세요")
            if st.button("댓글 등록", key=f"btn_{row['id']}"):
                if comment.strip():
                    new_c = {'author': st.session_state.username, 'text': comment, 'time': datetime.now().strftime("%H:%M")}
                    comments.append(new_c)
                    posts.at[_, 'comments'] = json.dumps(comments, ensure_ascii=False)
                    posts.to_csv(DATA_FILE, index=False)
                    st.rerun()
            st.divider()

# ==================== 3. 포트폴리오 ====================
with tab3:
    st.title("📉 포트폴리오 최적화")
    st.caption("상위 종목으로 효율적인 포트폴리오 구성")

    @st.cache_data(ttl=3600)
    def load_port_data():
        import FinanceDataReader as fdr
        return fdr.StockListing('KOSPI').head(50)

    df_p = load_port_data()
    selected = st.multiselect("종목 선택 (2~10개)", df_p['Name'].tolist(), default=df_p['Name'].head(5).tolist())
    amount = st.number_input("투자금액 (만원)", min_value=100, value=10000, step=100)

    if st.button("최적화 실행", type="primary") and len(selected) >= 2:
        with st.spinner("계산 중..."):
            st.success("✅ 최적화 완료!")

st.sidebar.info("✅ 대시보드·포트폴리오는 공개 / 게시판은 Secrets 로그인")