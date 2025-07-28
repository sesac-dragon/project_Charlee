import pandas as pd
from api.account import get_accounts
from strategy.casino_strategy import generate_buy_orders

def run_buy_entry_flow(setting_df: pd.DataFrame, buy_log_df: pd.DataFrame, current_prices: dict) -> pd.DataFrame:
    """매수 진입 흐름을 실행하고, 생성된 매수 주문 목록을 반환합니다."""
    print("\n[Flow] 매수 전략 실행")
    accounts = get_accounts()
    coin_balances = [a for a in accounts if a['currency'] != 'KRW' and float(a['balance']) > 0]
    print(f"[Flow] 현재 보유 코인 수: {len(coin_balances)}개")

    # 보유 코인이 없으면 카지노 매수 전략 실행
    if not coin_balances:
        print("[Flow] 보유 코인이 없으므로, 신규 매수 전략을 시작합니다.")
        buy_orders_df = generate_buy_orders(setting_df, buy_log_df, current_prices)
        return buy_orders_df
    else:
        print("[Flow] 이미 보유한 코인이 있으므로 신규 매수를 건너뜁니다.")
        return pd.DataFrame()