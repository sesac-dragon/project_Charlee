
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import sys
import random
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# --- 1. 시스템 경로 설정 및 기본 설정 ---

# 프로젝트 루트 경로를 시스템 경로에 추가하여 다른 모듈(api, utils 등)을 임포트할 수 있도록 함
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from api.order import get_orders
from api.account import get_accounts
from api.price import get_minute_candles, get_current_ask_price

def setup_page():
    """Streamlit 페이지의 기본 설정을 구성합니다."""
    st.set_page_config(
        page_title="모아봐요 코인의 숲 - 너굴의 투자 대시보드",
        page_icon="🌳",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def load_css(file_path):
    """외부 CSS 파일을 로드하여 페이지에 적용합니다."""
    try:
        with open(file_path, encoding='UTF-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS 파일을 찾을 수 없습니다: {file_path}")


# --- 2. 데이터 로딩 및 처리 ---

@st.cache_data(ttl=60)  # 60초마다 데이터 갱신
def load_all_data():
    """거래소 API로부터 모든 필요한 데이터를 로드하고, 로드 실패 시 더미 데이터를 반환합니다."""
    try:
        done_orders = get_orders(state='done')
        wait_orders = get_orders(state='wait')
        accounts_info = get_accounts()
        return pd.DataFrame(done_orders), pd.DataFrame(wait_orders), accounts_info
    except Exception as e:
        st.error(f"API 데이터 로딩 중 오류 발생: {e}. 데모용 더미 데이터로 표시됩니다.")
        dummy_done = []
        dummy_wait = []
        dummy_accounts = [{'currency': 'DOGE', 'balance': '100', 'avg_buy_price': '150'}, {'currency': 'KRW', 'balance': '100000', 'avg_buy_price': '0'}]
        return pd.DataFrame(dummy_done), pd.DataFrame(dummy_wait), dummy_accounts

def process_data(done_df, accounts_info):
    """로드된 데이터를 분석 및 계산하여 주요 지표들을 추출합니다."""
    if not done_df.empty:
        for col in ['price', 'volume']:
            done_df[col] = pd.to_numeric(done_df[col], errors='coerce')
        done_df['created_at'] = pd.to_datetime(done_df['created_at'])

    buy_df = done_df[done_df['side'] == 'bid'].copy() if not done_df.empty else pd.DataFrame()
    sell_df = done_df[done_df['side'] == 'ask'].copy() if not done_df.empty else pd.DataFrame()

    total_investment = 0
    total_valuation = 0
    assets = [acc for acc in accounts_info if acc.get('currency') != 'KRW' and (float(acc.get('balance', 0)) > 0 or float(acc.get('locked', 0)) > 0)]

    for asset in assets:
        balance = float(asset.get('balance', 0))
        avg_buy_price = float(asset.get('avg_buy_price', 0))
        investment = avg_buy_price * balance
        total_investment += investment
        
        try:
            current_price = get_current_ask_price(f"KRW-{asset['currency']}")
            total_valuation += current_price * balance
        except Exception:
            total_valuation += investment # 현재가 조회 실패 시 매수 금액으로 평가

    total_profit = total_valuation - total_investment
    profit_rate = (total_profit / total_investment * 100) if total_investment > 0 else 0
    
    return buy_df, sell_df, assets, total_investment, total_valuation, total_profit, profit_rate


import docker

# --- 3. UI 렌더링 함수 ---

def render_docker_status():
    """현재 실행 중인 Docker 컨테이너 목록을 가져와 대시보드에 표시합니다."""
    st.sidebar.subheader("🐳 도커 컨테이너 현황")
    try:
        client = docker.from_env()
        containers = client.containers.list()
        
        if containers:
            container_data = []
            for c in containers:
                status = c.status
                if status == "running":
                    status_icon = "✅"
                elif status == "exited":
                    status_icon = "❌"
                else:
                    status_icon = "⏳"
                
                container_data.append({
                    "컨테이너 이름": c.name,
                    "상태": f"{status_icon} {status.capitalize()}",
                    "이미지": c.image.tags[0] if c.image.tags else "N/A",
                })
            
            df = pd.DataFrame(container_data)
            st.sidebar.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.sidebar.info("실행 중인 컨테이너가 없습니다.")

    except Exception as e:
        st.sidebar.error(f"Docker 정보를 가져올 수 없습니다.\n(Docker 소켓 연결 확인 필요)")




def render_sidebar(total_investment, profit_rate, wait_df, buy_df, sell_df):
    """사이드바 UI를 렌더링합니다."""
    with st.sidebar:
        st.title("너굴의 투자 비서 🦝")
        st.markdown("---")
        st.subheader("💬 너굴의 한마디")

        comments = []
        if total_investment > 0:
            if profit_rate > 5: comments.append("오늘 농사는 풍년이네요! 🌳")
            elif profit_rate > 0: comments.append("씨앗들이 무럭무럭 자라고 있어요. 🌱")
            else: comments.append("지금은 씨앗을 심을 때예요. 💧")
        
        if not wait_df.empty: comments.append(f"현재 {len(wait_df)}개의 주문을 기다리고 있어요. 🎣")
        
        now_utc = pd.to_datetime('now', utc=True)
        if not buy_df.empty and (now_utc - buy_df['created_at'].max()).total_seconds() < 3600:
            comments.append("최근에 새로운 씨앗을 심었어요! 🌱")
        if not sell_df.empty and (now_utc - sell_df['created_at'].max()).total_seconds() < 3600:
            comments.append("방금 잘 익은 열매를 수확했답니다! 🍅")

        st.info(random.choice(comments) if comments else "느긋하게 강태공처럼 기다리는 중... 🎣")
        st.markdown("---")
        st.button("새로고침", use_container_width=True)


def render_header_and_info():
    """페이지의 헤더와 정보 Expander를 렌더링합니다."""
    st.title("🌳 모아봐요 코인의 숲 🌳")
    st.markdown("##### 24시간 잠들지 않는 AI 주민 '너굴'과 함께, 스트레스 없는 코인 투자를 시작해보세요!")
    st.markdown("---")

def render_architecture_expander():
    """프로젝트 아키텍처 정보를 Expander UI로 렌더링합니다."""
    with st.expander("🛠️ '코인의 숲'은 어떻게 만들어졌나요?", expanded=True):
        # 가독성과 디자인을 개선한 새로운 아키텍처 다이어그램
        mermaid_code = '''graph TD
    %% --- 스타일 정의 --- 
    classDef user fill:#E0F2F1,stroke:#00796B,stroke-width:2px,color:#004D40,font-size:14px
    classDef system fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#1B5E20,font-size:14px
    classDef external fill:#FFFDE7,stroke:#FBC02D,stroke-width:2px,color:#F57F17,font-size:14px
    classDef db fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#0D47A1,font-size:14px

    subgraph "🌳 코인의 숲 (사용자 영역)"
        A["🧑‍🌾 사용자<br/>(Farmer)"]
        C{{"📊 대시보드<br/>(Streamlit)"}}
        A -- "1. '씨앗 농법' 전략 설정" --> B["🏡 AI 주민 '너굴'<br/>(Docker System)"];
        A -- "4. 숲 현황 구경하기" --> C;
    end

    subgraph "🏡 AI 주민 '너굴' (자동매매 시스템)"
        B -- "2. '씨앗 농법' 실행" --> D["🤖 너굴<br/>(Core Engine)"]
        D --> E["🌱 매매 전략<br/>(Strategy)"]
        E -- "시장 분석" --> F["📞 거래소 통신<br/>(API)"]
        E -- "매매 신호" --> G["💪 주문 실행<br/>(Manager)"]
        G -- "주문 제출" --> F
        G -- "3. 농사일지 기록" --> H[("📔 데이터베이스<br/>(DB)")]
    end

    subgraph "외부 세계"
        I["🏦 거래소 API"]
    end

    F -- "실시간 정보 요청" --> I
    C -- "최신 현황 조회" --> F
    C -- "과거 농사일지 조회" --> H

    %% --- 스타일 적용 --- 
    class A,C user
    class B,D,E,F,G system
    class I external
    class H db
'''
        
        html_code = f'''
            <div class="mermaid" style="text-align: center;">
{mermaid_code}
            </div>
            <script src="https://cdn.jsdelivr.net/npm/mermaid@9.4.3/dist/mermaid.min.js"></script>
            <script>
                mermaid.initialize({{ startOnLoad: true }});
            </script>
        '''
        
        # 다이어그램이 잘리지 않도록 높이를 1000으로 조정
        components.html(html_code, height=1000)


def render_summary_metrics(total_investment, total_valuation, total_profit, profit_rate, wait_df):
    """주요 투자 현황 지표를 메트릭 카드 형태로 렌더링합니다."""
    st.subheader("💰 너굴의 실시간 투자 현황")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 매수 금액", f"{total_investment:,.0f} KRW")
    col2.metric("총 평가 금액", f"{total_valuation:,.0f} KRW", f"{total_profit:,.0f} KRW")
    col3.metric("수익률", f"{profit_rate:.2f} %")
    col4.metric("⏳ 주문 대기 중", f"{len(wait_df)} 건")
    st.markdown("---")

def render_portfolio_pie_chart(assets):
    """포트폴리오 자산 비중을 파이 차트로 렌더링합니다."""
    st.subheader("📊 너굴의 자산 주머니")
    if assets:
        asset_df = pd.DataFrame(assets)
        asset_df['balance'] = pd.to_numeric(asset_df['balance'])
        asset_df['avg_buy_price'] = pd.to_numeric(asset_df['avg_buy_price'])
        asset_df['valuation'] = asset_df['avg_buy_price'] * asset_df['balance']
        
        fig = px.pie(asset_df, values='valuation', names='currency', title='코인별 자산 비중', hole=.3,
                     color_discrete_sequence=px.colors.sequential.Aggrnyl)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("현재 보유 중인 자산이 없습니다.")
    st.markdown("---")

def render_trading_chart(done_df, buy_df, sell_df, assets):
    """매매 시점을 분석하는 캔들스틱 차트를 렌더링합니다."""
    st.subheader("📈 매매 시점 분석")
    if not done_df.empty:
        market_list = done_df['market'].unique()
        
        # done_df가 비어있지 않으면 첫 번째 마켓을 기본으로 선택
        default_market_index = 0 if market_list.size > 0 else None
        selected_market = st.selectbox('분석할 마켓을 선택하세요:', market_list, index=default_market_index)
        
        if selected_market:
            try:
                candles = get_minute_candles(market=selected_market, unit=5, count=200)
                candle_df = pd.DataFrame(candles)
                
                numeric_cols = ['opening_price', 'high_price', 'low_price', 'trade_price', 'candle_acc_trade_volume']
                candle_df[numeric_cols] = candle_df[numeric_cols].apply(pd.to_numeric)
                candle_df['candle_date_time_kst'] = pd.to_datetime(candle_df['candle_date_time_kst'])
                candle_df = candle_df.sort_values(by='candle_date_time_kst')

                candle_df['ma5'] = candle_df['trade_price'].rolling(window=5).mean()
                candle_df['ma20'] = candle_df['trade_price'].rolling(window=20).mean()

                # 볼린저 밴드 계산 (20일 기준)
                window_size = 20
                candle_df['stddev'] = candle_df['trade_price'].rolling(window=window_size).std()
                candle_df['upper_band'] = candle_df['ma20'] + 2 * candle_df['stddev']
                candle_df['lower_band'] = candle_df['ma20'] - 2 * candle_df['stddev']

                market_buy_df = buy_df[buy_df['market'] == selected_market]
                market_sell_df = sell_df[sell_df['market'] == selected_market]
                
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.05, subplot_titles=(f'{selected_market} 가격', '거래량'), 
                                    row_heights=[0.7, 0.3])

                # 캔들스틱 차트
                fig.add_trace(go.Candlestick(x=candle_df['candle_date_time_kst'],
                                             open=candle_df['opening_price'],
                                             high=candle_df['high_price'],
                                             low=candle_df['low_price'],
                                             close=candle_df['trade_price'],
                                             name='캔들',
                                             increasing_line_color='rgb(30, 150, 255)', decreasing_line_color='rgb(255, 80, 80)'), row=1, col=1)
                
                # 이동평균선
                fig.add_trace(go.Scatter(x=candle_df['candle_date_time_kst'], y=candle_df['ma5'], mode='lines', name='MA5', line=dict(color='rgb(0, 150, 136)', width=1)), row=1, col=1)
                fig.add_trace(go.Scatter(x=candle_df['candle_date_time_kst'], y=candle_df['ma20'], mode='lines', name='MA20', line=dict(color='rgb(156, 39, 176)', width=1)), row=1, col=1)

                # 볼린저 밴드
                fig.add_trace(go.Scatter(x=candle_df['candle_date_time_kst'], y=candle_df['upper_band'], mode='lines', name='Upper Band', line=dict(color='rgba(150, 150, 150, 0.5)', width=1)), row=1, col=1)
                fig.add_trace(go.Scatter(x=candle_df['candle_date_time_kst'], y=candle_df['lower_band'], mode='lines', name='Lower Band', line=dict(color='rgba(150, 150, 150, 0.5)', width=1), fill='tonexty', fillcolor='rgba(150, 150, 150, 0.1)'), row=1, col=1)

                # 매수 마커 강조
                if not market_buy_df.empty:
                    fig.add_trace(go.Scatter(x=market_buy_df['created_at'], y=market_buy_df['price'], mode='markers', name='매수',
                                             marker=dict(color='rgb(30, 150, 255)', size=12, symbol='triangle-up', line=dict(width=2, color='rgb(0, 100, 200)')),
                                             hoverinfo='text',
                                             hovertext=market_buy_df.apply(lambda row: f"매수: {row['market']}<br>가격: {row['price']:,}<br>수량: {row['volume']:.8f}<br>시간: {row['created_at']}", axis=1)), row=1, col=1)
                # 매도 마커 강조
                if not market_sell_df.empty:
                    fig.add_trace(go.Scatter(x=market_sell_df['created_at'], y=market_sell_df['price'], mode='markers', name='매도',
                                             marker=dict(color='rgb(255, 80, 80)', size=12, symbol='triangle-down', line=dict(width=2, color='rgb(200, 0, 0)')),
                                             hoverinfo='text',
                                             hovertext=market_sell_df.apply(lambda row: f"매도: {row['market']}<br>가격: {row['price']:,}<br>수량: {row['volume']:.8f}<br>시간: {row['created_at']}", axis=1)), row=1, col=1)

                # 현재가 라인 추가
                try:
                    current_price_val = get_current_ask_price(selected_market)
                    fig.add_hline(y=current_price_val, line_dash="dash", line_color="rgb(0, 120, 215)", name="현재가",
                                  annotation_text=f"현재가: {current_price_val:,.2f}",
                                  annotation_position="top right", row=1, col=1)
                except Exception as e:
                    st.warning(f"현재가 정보를 가져올 수 없습니다: {e}")

                # 평균 매수 가격 라인 추가
                holding_asset = next((asset for asset in assets if f"KRW-{asset['currency']}" == selected_market), None)
                if holding_asset and float(holding_asset.get('balance', 0)) > 0:
                    avg_buy_price = float(holding_asset.get('avg_buy_price', 0))
                    fig.add_hline(y=avg_buy_price, line_dash="dot", line_color="rgb(200, 0, 0)", name="평균 매수 가격",
                                  annotation_text=f"평균 매수 가격: {avg_buy_price:,.2f}",
                                  annotation_position="bottom right", row=1, col=1)

                # 거래량 차트
                fig.add_trace(go.Bar(x=candle_df['candle_date_time_kst'], y=candle_df['candle_acc_trade_volume'], name='거래량', marker_color='rgb(150, 150, 150)'), row=2, col=1)

                fig.update_layout(title_text=f'{selected_market} 매매 시점 분석', template='plotly_white',
                                  xaxis_rangeslider_visible=True, 
                                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                  height=800,
                                  xaxis_range=[candle_df['candle_date_time_kst'].iloc[-5], candle_df['candle_date_time_kst'].iloc[-1]] if len(candle_df) >= 5 else None
                                 )
                fig.update_yaxes(title_text="가격 (KRW)", range=[280, 330], row=1, col=1)
                fig.update_yaxes(title_text="거래량", row=2, col=1)
                
                st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"차트 데이터를 가져오는 중 오류 발생: {e}")
    else:
        st.info("분석할 거래 기록이 없습니다.")


def render_data_tabs(wait_df, done_df):
    """주문 대기열과 전체 거래 기록을 탭 형태로 렌더링합니다."""
    tab1, tab2 = st.tabs(["⏳ 주문 대기열", "📚 전체 거래 기록"])

    with tab1:
        if not wait_df.empty:
            wait_display_df = wait_df[['created_at', 'market', 'side', 'ord_type', 'price', 'volume']].copy()
            wait_display_df.columns = ['주문시간', '마켓', '종류', '주문방식', '주문가격', '주문수량']
            wait_display_df['주문가격'] = pd.to_numeric(wait_display_df['주문가격']).map('{:,.2f}'.format)
            wait_display_df['주문수량'] = pd.to_numeric(wait_display_df['주문수량']).map('{:,.8f}'.format)
            st.dataframe(wait_display_df, use_container_width=True, hide_index=True)
        else:
            st.info("현재 대기 중인 주문이 없습니다.")

    with tab2:
        st.dataframe(done_df, use_container_width=True, hide_index=True)


# --- 4. 메인 애플리케이션 실행 ---

def main():
    """메인 함수: 앱의 전체 흐름을 제어합니다."""
    setup_page()
    load_css("streamlit_app/style/style.css")

    done_df, wait_df, accounts_info = load_all_data()
    buy_df, sell_df, assets, total_investment, total_valuation, total_profit, profit_rate = process_data(done_df, accounts_info)

    render_sidebar(total_investment, profit_rate, wait_df, buy_df, sell_df)
    render_header_and_info()
    render_architecture_expander()
    render_summary_metrics(total_investment, total_valuation, total_profit, profit_rate, wait_df)
    render_portfolio_pie_chart(assets)
    
    # 거래 기록 및 분석 섹션
    st.header("📑 거래 기록 및 분석")
    tab1, tab2 = st.tabs(["📈 매매 시점 분석", "🗃️ 상세 데이터"])
    with tab1:
        render_trading_chart(done_df, buy_df, sell_df, assets)
    with tab2:
        render_data_tabs(wait_df, done_df)


if __name__ == "__main__":
    main()
