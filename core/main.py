

import time
import pandas as pd
from apscheduler.schedulers.blocking import BlockingScheduler
from strategy.buy_entry import run_buy_entry_flow
from strategy.sell_entry import run_sell_entry_flow
from manager.order_executor import execute_buy_orders, execute_sell_orders
from utils.file_utils import load_csv
from api.price import get_current_ask_price

import traceback

def trading_cycle():
    """한 번의 전체 매매 사이클을 실행합니다."""
    print("\n---")
    print(f"[{pd.Timestamp.now()}] 새로운 거래 사이클 시작")
    try:
        

        setting_df = load_csv("setting.csv")
        buy_log_df = load_csv("buy_log.csv")
        sell_log_df = load_csv("sell_log.csv")

        # 1. 현재가 조회
        markets = setting_df['market'].tolist()
        current_prices = {}
        for market in markets:
            try:
                current_prices[market] = get_current_ask_price(market)
            except Exception as e:
                print(f"[main] {market} 현재가 조회 실패: {e}")
        if not current_prices:
            print("[main] 현재가 정보를 가져올 수 없습니다.")
            return

        # 2. 매수/매도 전략 실행하여 주문 목록 생성
        buy_orders_to_execute = run_buy_entry_flow(setting_df, buy_log_df, current_prices)
        sell_orders_to_execute = run_sell_entry_flow(setting_df, sell_log_df)

        # 3. 생성된 주문 목록 실행
        if not buy_orders_to_execute.empty:
            execute_buy_orders(buy_orders_to_execute)
        
        if not sell_orders_to_execute.empty:
            execute_sell_orders(sell_orders_to_execute)

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"[main] 거래 사이클 중 예외 발생: {e}")
        print(f"[main] 상세 오류:\n{error_details}")
    finally:
        print("[main] 거래 사이클 종료")
        print("---")

if __name__ == "__main__":
    print(f"[Scheduler] 자동 거래 시스템 스케줄러를 시작합니다.")
    scheduler = BlockingScheduler()
    # 1분마다 trading_cycle 함수를 실행합니다.
    scheduler.add_job(trading_cycle, 'interval', minutes=1)
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("[Scheduler] 스케줄러를 종료합니다.")