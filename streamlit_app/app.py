# streamlit_app/app.py
import os
import sys

import time
import requests
import pymysql
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# 0) 환경 변수 로드 (.env 없으면 각자 채워 넣어도 됩니다)
# ---------------------------------------------------------------------
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "coin_trade_db")

# ---------------------------------------------------------------------
# 1) 업비트 현재가 직접 호출 (api.* 사용 안 함)
# ---------------------------------------------------------------------
def get_now_price(market: str) -> float | None:
    try:
        url = "https://api.upbit.com/v1/orderbook"
        res = requests.get(url, params={"markets": market}, timeout=3)
        res.raise_for_status()
        data = res.json()
        return float(data[0]["orderbook_units"][0]["ask_price"])
    except Exception as e:
        st.error(f"❌ 현재가 조회 실패: {e}")
        return None

# ---------------------------------------------------------------------
# 2) DB 연결 (없으면 None을 리턴 → 그래프만 표시)
# ---------------------------------------------------------------------
def get_conn():
    try:
        return pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
    except Exception as e:
        st.warning(f"DB 연결 실패: {e}")
        return None

# ---------------------------------------------------------------------
# 3) 체결 로그 조회 (buy_log / sell_log) - api 없이 직접 SQL
# ---------------------------------------------------------------------
def fetch_trade_logs(table: str) -> pd.DataFrame:
    conn = get_conn()
    if conn is None:
        return pd.DataFrame(columns=["time", "price"])

    # 테이블별 가격 컬럼 분기
    if table == "buy_log":
        price_col = "target_price"
    elif table == "sell_log":
        price_col = "target_sell_price"
    else:
        raise ValueError("table must be 'buy_log' or 'sell_log'")

    query = f"""
        SELECT time, {price_col} AS price
        FROM {table}
        WHERE filled = 'done'
        ORDER BY time DESC
        LIMIT 100
    """

    try:
        df = pd.read_sql(query, conn)
        conn.close()
        if not df.empty:
            df["time"] = pd.to_datetime(df["time"])
        return df
    except Exception as e:
        st.warning(f"{table} 조회 실패: {e}")
        return pd.DataFrame(columns=["time", "price"])

# ---------------------------------------------------------------------
# 4) Streamlit 화면
# ---------------------------------------------------------------------
st.set_page_config(page_title="📊 실시간 매매 대시보드", layout="wide")
st.title("📊 실시간 매매 대시보드")

# 사이드바 옵션
st.sidebar.header("⚙️ 옵션")
market = st.sidebar.text_input("마켓", value="KRW-DOGE")
refresh_sec = st.sidebar.number_input("자동 새로고침(초)", min_value=0, value=0, step=1)
keep_points = st.sidebar.number_input("가격 기록 개수(최근 N개)", min_value=10, value=100, step=10)

# (선택) streamlit-autorefresh 사용
try:
    if refresh_sec > 0:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=refresh_sec * 1000, key="auto_refresh")
except Exception:
    if refresh_sec > 0:
        st.info("자동 새로고침을 쓰려면 `pip install streamlit-autorefresh` 설치하세요.")

# 가격 데이터 세션에 보관
if "price_data" not in st.session_state:
    st.session_state.price_data = []

# 현재가 조회
price = get_now_price(market)
now = datetime.now()

if price is not None:
    st.session_state.price_data.append({"time": now, "price": price})

# 최근 N개 자르기
price_df = pd.DataFrame(st.session_state.price_data[-keep_points:])
if not price_df.empty:
    price_df["time"] = pd.to_datetime(price_df["time"])

# 체결 로그 불러오기 (DB 연결 안되면 빈 DF)
buy_df = fetch_trade_logs("buy_log")
sell_df = fetch_trade_logs("sell_log")

# 상단: 현재가/업데이트 시간
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("현재가", f"{price:,.2f} KRW" if price is not None else "조회 실패")
with col2:
    st.write("업데이트:", now.strftime("%Y-%m-%d %H:%M:%S"))
with col3:
    st.write("기록된 가격 포인트:", len(price_df))

st.markdown("---")

# 메인 차트: 실시간 가격 + 체결 마킹
st.subheader("📈 실시간 가격 + 체결 마킹")

if not price_df.empty:
    base = alt.Chart(price_df).mark_line(color="steelblue").encode(
        x=alt.X("time:T", title="시간"),
        y=alt.Y("price:Q", title="가격")
    ).properties(height=450)

    layers = [base]

    if not buy_df.empty:
        buy_layer = alt.Chart(buy_df).mark_point(
            size=80, color="green", shape="circle"
        ).encode(
            x="time:T",
            y="price:Q",
            tooltip=["time:T", "price:Q"]
        )
        layers.append(buy_layer)

    if not sell_df.empty:
        sell_layer = alt.Chart(sell_df).mark_point(
            size=100, color="red", shape="triangle"
        ).encode(
            x="time:T",
            y="price:Q",
            tooltip=["time:T", "price:Q"]
        )
        layers.append(sell_layer)

    st.altair_chart(alt.layer(*layers).resolve_scale(y='shared'), use_container_width=True)
else:
    st.warning("아직 가격 데이터가 없습니다. 잠시 후 새로고침 해보세요.")

st.markdown("---")

# 하단: 최근 체결 로그 표
st.subheader("🧾 최근 체결 로그")
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**🟢 매수 체결 (buy_log)**")
    st.dataframe(buy_df.sort_values("time", ascending=False), use_container_width=True)
with col_b:
    st.markdown("**🔴 매도 체결 (sell_log)**")
    st.dataframe(sell_df.sort_values("time", ascending=False), use_container_width=True)

# 수동 새로고침
st.markdown("---")
if st.button("🔄 수동 새로고침"):
    # 최신 streamlit이면 st.rerun(), 아니면 experimental_rerun()
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


