

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
    # --- [1. 사이클 시작] ---
    # 이 함수는 스케줄러에 의해 1분마다 호출되며, 자동매매의 전체 과정을 담당합니다.
    print("\n---")
    print(f"[{pd.Timestamp.now()}] 새로운 거래 사이클 시작")
    try:
        
        # --- [2. 설정 및 로그 로드] ---
        # 사용자가 정의한 매매 설정(setting.csv)과 과거의 거래 기록(log)을 불러옵니다.
        # 이 데이터를 기반으로 다음 행동을 결정합니다.
        setting_df = load_csv("setting.csv")
        buy_log_df = load_csv("buy_log.csv")
        sell_log_df = load_csv("sell_log.csv")

        # --- [3. 현재 시장 상황 파악] ---
        # 매매 판단의 가장 중요한 기준인 현재 코인 가격을 Upbit API를 통해 조회합니다.
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

        # --- [4. 매매 전략 실행 (두뇌)] ---
        # 현재 가격과 과거 기록을 바탕으로, strategy 폴더의 핵심 로직을 실행합니다.
        # 이 단계에서 "살까?", "팔까?"를 고민하여 실제 실행할 주문 목록을 생성합니다.
        buy_orders_to_execute = run_buy_entry_flow(setting_df, buy_log_df, current_prices)
        sell_orders_to_execute = run_sell_entry_flow(setting_df, sell_log_df)

        # --- [5. 주문 실행 (손과 발)] ---
        # 전략에 의해 생성된 주문 목록이 있다면, manager 폴더의 실행 로직을 통해
        # Upbit 거래소에 실제 매수/매도 주문을 넣습니다.
        if not buy_orders_to_execute.empty:
            execute_buy_orders(buy_orders_to_execute)
        
        if not sell_orders_to_execute.empty:
            execute_sell_orders(sell_orders_to_execute)

    except Exception as e:
        # 예외 처리: 어떤 오류가 발생하더라도 시스템 전체가 멈추지 않도록 방지합니다.
        error_details = traceback.format_exc()
        print(f"[main] 거래 사이클 중 예외 발생: {e}")
        print(f"[main] 상세 오류:\n{error_details}")
    finally:
        print("[main] 거래 사이클 종료")
        print("---")

if __name__ == "__main__":
    # --- [0. 스케줄러 시작] ---
    # 이 프로그램의 시작점입니다.
    # APScheduler를 사용하여 1분마다 trading_cycle 함수를 주기적으로 실행시킵니다.
    # Docker 컨테이너가 실행되면 이 부분이 가장 먼저 작동합니다.
    print(f"[Scheduler] 자동 거래 시스템 스케줄러를 시작합니다.")
    scheduler = BlockingScheduler()
    scheduler.add_job(trading_cycle, 'interval', minutes=1)
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("[Scheduler] 스케줄러를 종료합니다.")