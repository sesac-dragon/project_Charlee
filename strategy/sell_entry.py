import pandas as pd
from api.account import get_accounts
from api.price import get_current_ask_price
from strategy.casino_strategy import generate_sell_orders

def get_current_holdings(setting_df: pd.DataFrame) -> dict:
    """현재 보유 자산 정보를 조회하고, 각 자산의 상세 정보를 계산합니다."""
    accounts = get_accounts()
    holdings = {}

    for acc in accounts:
        if acc['currency'] == 'KRW':
            continue

        market = f"KRW-{acc['currency']}"
        if market not in setting_df['market'].values:
            continue

        balance = float(acc['balance'])
        locked = float(acc['locked'])
        avg_price = float(acc['avg_buy_price'])

        if balance + locked == 0:
            continue

        holdings[market] = {
            "balance": balance,
            "locked": locked,
            "avg_price": avg_price,
        }
    return holdings

def run_sell_entry_flow(setting_df: pd.DataFrame, sell_log_df: pd.DataFrame) -> pd.DataFrame:
    """매도 진입 흐름을 실행하고, 생성된 매도 주문 목록을 반환합니다."""
    print("\n[Flow] 매도 전략 실행")
    holdings = get_current_holdings(setting_df)

    if not holdings:
        print("[Flow] 매도할 코인이 없습니다.")
        return pd.DataFrame()
    
    print(f"[Flow] 현재 보유 코인: {list(holdings.keys())}")
    sell_orders_df = generate_sell_orders(setting_df, holdings, sell_log_df)
    return sell_orders_df