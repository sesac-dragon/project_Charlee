import pandas as pd
import pymysql
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time

from api.price import get_minute_candles
from strategy.casino_strategy import generate_buy_orders, generate_sell_orders

# 환경 변수 로딩 (.env에서)
load_dotenv()
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

INITIAL_CASH = 10_000_000
BUY_FEE = 0.0005
SELL_FEE = 0.0005

MIN_CASH_RATIO = 0.3     # 전체 자산 중 최소 보유 현금 비율
STOP_LOSS_PCT = 0.05     # 손절 기준 5%


def save_to_db(df: pd.DataFrame):
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset='utf8mb4'
    )
    cursor = conn.cursor()

    insert_query = """
        INSERT INTO backtest_result (
            time, market, open, high, close, `signal`,
            trade_amount, avg_price, gap_pct, total_buy_amount,
            realized_pnl, cash, trade_fee, total_fee, portfolio_value
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    for _, row in df.iterrows():
        cursor.execute(insert_query, (
            row["시간"], row["마켓"], row["시가"], row["고가"], row["종가"],
            row["신호"], row["매매금액"], row["현재 평단가"],
            row["현재 종가와 평단가의 gap(%)"], row["누적 매수금"],
            row["실현 손익"], row["보유 현금"], row["거래시 수수료"],
            row["총 누적 수수료"], row["총 포트폴리오 가치"]
        ))

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ 시뮬레이션 결과 DB 저장 완료")


def simulate_with_strategy(market: str, start: str, end: str, unit: int,
                            unit_size: float, small_flow_pct: float, small_flow_units: int,
                            large_flow_pct: float, large_flow_units: int, take_profit_pct: float,
                            filename: str = None):

    print(f"[simulator] ⏱️ 시뮬레이션 시작 - {market}, {start} ~ {end}, unit: {unit}분")

    current_time = pd.to_datetime(start)
    end_time = pd.to_datetime(end)
    all_candles = []

    while current_time < end_time:
        to_time = (current_time + timedelta(minutes=unit * 200)).strftime("%Y-%m-%d %H:%M:%S")
        try:
            candles = get_minute_candles(market, unit=unit, count=200, to=to_time)
            if not candles:
                break
            candles.reverse()
            all_candles.extend(candles)
            last_dt = pd.to_datetime(candles[0]['candle_date_time_kst'])
            current_time = last_dt + timedelta(minutes=unit)
            time.sleep(0.3)
        except Exception as e:
            print(f"[경고] 분봉 데이터 조회 실패 → 재시도 대기: {e}")
            time.sleep(5)

    df = pd.DataFrame(all_candles)
    df["시간"] = pd.to_datetime(df["candle_date_time_kst"])
    df = df[["시간", "opening_price", "high_price", "low_price", "trade_price"]]
    df.columns = ["시간", "시가", "고가", "저가", "종가"]
    df["마켓"] = market

    setting_df = pd.DataFrame([{
        "market": market,
        "unit_size": unit_size,
        "small_flow_pct": small_flow_pct,
        "small_flow_units": small_flow_units,
        "large_flow_pct": large_flow_pct,
        "large_flow_units": large_flow_units,
        "take_profit_pct": take_profit_pct
    }])

    cash = INITIAL_CASH
    holdings = {}
    buy_log_df = pd.DataFrame(columns=[
        "time", "market", "target_price", "buy_amount", "buy_units", "buy_type", "buy_uuid", "filled"
    ])
    sell_log_df = pd.DataFrame(columns=[
        "market", "avg_buy_price", "quantity", "target_sell_price", "sell_uuid", "filled"
    ])

    realized_pnl = 0.0
    total_buy_amount = 0.0
    total_buy_volume = 0.0
    cumulative_fee = 0.0
    last_trade_fee = 0.0
    last_trade_amount = 0.0
    logs = []

    for _, row in df.iterrows():
        now = row["시간"]
        current_price = row["종가"]
        events = []

        current_prices = {market: current_price}
        buy_log_df = generate_buy_orders(setting_df, buy_log_df, current_prices)

        for idx, r in buy_log_df.iterrows():
            if r["filled"] in ["update", "wait"] and r["market"] == market:
                price = r["target_price"]
                amount = r["buy_amount"]
                buy_type = r["buy_type"]

                portfolio_value = cash + holdings.get(market, 0) * current_price
                cash_ratio = cash / portfolio_value if portfolio_value > 0 else 1

                if buy_type == "initial" or current_price <= price:
                    if cash >= amount and cash_ratio >= MIN_CASH_RATIO:
                        fee = amount * BUY_FEE
                        volume = (amount - fee) / price
                        cash -= amount
                        cumulative_fee += fee
                        total_buy_amount += amount
                        total_buy_volume += volume
                        holdings[market] = holdings.get(market, 0) + volume
                        buy_log_df.at[idx, "filled"] = "done"
                        last_trade_amount = amount
                        last_trade_fee = fee

                        events.append(f"{buy_type} 매수")
                    else:
                        buy_log_df.at[idx, "filled"] = "wait"
                else:
                    buy_log_df.at[idx, "filled"] = "wait"

        if market in holdings and holdings[market] > 0:
            balance = holdings[market]
            avg_buy_price = total_buy_amount / total_buy_volume if total_buy_volume > 0 else 0

            if avg_buy_price > 0 and (current_price - avg_buy_price) / avg_buy_price <= -STOP_LOSS_PCT:
                volume = holdings[market]
                fee = volume * current_price * SELL_FEE
                proceeds = volume * current_price - fee
                pnl = (current_price - avg_buy_price) * volume

                cash += proceeds
                cumulative_fee += fee
                realized_pnl += pnl - fee
                holdings[market] = 0
                sell_log_df = sell_log_df[sell_log_df["market"] != market]
                buy_log_df = buy_log_df[buy_log_df["market"] != market]
                total_buy_amount = 0.0
                total_buy_volume = 0.0
                last_trade_amount = proceeds
                last_trade_fee = fee
                events.append("손절")

            holdings_info = {
                market: {
                    "balance": balance,
                    "locked": 0,
                    "avg_price": avg_buy_price,
                    "current_price": current_price
                }
            }

            split_sell_levels = [
                (0.02, 0.3),
                (0.04, 0.3),
                (0.06, 1.0)
            ]

            for threshold, ratio in split_sell_levels:
                if avg_buy_price > 0 and (current_price - avg_buy_price) / avg_buy_price >= threshold:
                    volume = holdings[market] * ratio
                    fee = volume * current_price * SELL_FEE
                    proceeds = volume * current_price - fee
                    pnl = (current_price - avg_buy_price) * volume

                    cash += proceeds
                    cumulative_fee += fee
                    realized_pnl += pnl - fee
                    holdings[market] -= volume
                    last_trade_amount = proceeds
                    last_trade_fee = fee
                    events.append(f"분할매도: +{int(threshold * 100)}% {int(ratio * 100)}% 매도")

                    if holdings[market] <= 0.0000001:
                        holdings[market] = 0
                        buy_log_df = buy_log_df[buy_log_df["market"] != market]
                        total_buy_amount = 0.0
                        total_buy_volume = 0.0
                    break

            sell_log_df = generate_sell_orders(setting_df, holdings_info, sell_log_df)

            for idx, r in sell_log_df.iterrows():
                if r["filled"] == "update" and r["market"] == market:
                    target_price = r["target_sell_price"]
                    if current_price >= target_price:
                        volume = r["quantity"]
                        fee = volume * current_price * SELL_FEE
                        proceeds = volume * current_price - fee
                        pnl = (current_price - avg_buy_price) * volume

                        cash += proceeds
                        cumulative_fee += fee
                        realized_pnl += pnl - fee
                        holdings[market] = 0
                        sell_log_df.at[idx, "filled"] = "done"
                        buy_log_df = buy_log_df[buy_log_df["market"] != market]
                        total_buy_amount = 0.0
                        total_buy_volume = 0.0
                        last_trade_amount = proceeds
                        last_trade_fee = fee
                        events.append("매도")

        quantity = holdings.get(market, 0)
        avg_price = total_buy_amount / total_buy_volume if total_buy_volume > 0 else 0
        gap_pct = round((current_price - avg_price) / avg_price * 100, 2) if avg_price > 0 else 0
        portfolio_value = cash + quantity * current_price
        signal_str = " / ".join(events) if events else "보유"

        logs.append({
            "시간": now,
            "마켓": market,
            "시가": row["시가"],
            "고가": row["고가"],
            "종가": current_price,
            "신호": signal_str,
            "매매금액": round(last_trade_amount, 2),
            "현재 평단가": round(avg_price, 2),
            "현재 종가와 평단가의 gap(%)": gap_pct,
            "누적 매수금": round(total_buy_amount, 2),
            "실현 손익": round(realized_pnl, 2),
            "보유 현금": round(cash, 2),
            "거래시 수수료": round(last_trade_fee, 2),
            "총 누적 수수료": round(cumulative_fee, 2),
            "총 포트폴리오 가치": round(portfolio_value, 2)
        })

    result_df = pd.DataFrame(logs)
    save_to_db(result_df)

    filename = filename or f"전략_시뮬_{market}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    result_df.to_excel(filename, index=False)
    print(f"[simulator] ✅ 시뮬레이션 완료 → 결과 저장: {filename}")


    # ✅ DB에도 저장
    from utils.db import insert_backtest_result_to_db
    insert_backtest_result_to_db(result_df)

