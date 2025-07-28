import pandas as pd
from api.order import send_order, get_order_results_by_uuids_safe
from utils.price_utils import adjust_price_to_tick
from db.db_utils import insert_order

def execute_buy_orders(buy_orders_df: pd.DataFrame) -> None:
    """매수 주문 목록을 받아 실행하고, 체결된 주문을 DB에 저장합니다."""
    print(f"[Executor] 매수 주문 실행 시작: {len(buy_orders_df)}건")
    if buy_orders_df.empty:
        return

    for _, order in buy_orders_df.iterrows():
        market = order["market"]
        price = order["target_price"]
        amount = order["buy_amount"]
        buy_type = order["buy_type"]

        try:
            # 최소 주문 금액 체크
            if (buy_type == 'initial' and amount < 5000) or (buy_type != 'initial' and price * (amount / price) < 5000):
                print(f"⚠️ [Executor] {market} 매수 금액 최소 주문 금액 미달 → 스킵")
                continue

            print(f"🌟 [Executor] 신규 매수 주문: {market}, amount={amount}, price={price}")
            
            if buy_type == "initial":
                response = send_order(market=market, side="bid", ord_type="price", amount_krw=amount)
            else:
                volume = round(amount / price, 8)
                response = send_order(market=market, side="bid", ord_type="limit", unit_price=price, volume=volume)

            if 'error' in response:
                print(f"❌ [Executor] 주문 실패: {response['error']['message']}")
                continue

            uuid = response.get("uuid")
            if not uuid:
                print(f"❌ [Executor] 주문 후 UUID를 받지 못했습니다: {response}")
                continue

            # 체결 상태 확인 및 DB 저장
            final_order_status = get_order_results_by_uuids_safe([uuid])
            if final_order_status and final_order_status[0].get("state") == "done":
                print(f"✅ [Executor] {market} 매수 주문 체결 완료")
                db_data = final_order_status[0]
                insert_order(db_data, 'buy_orders')

        except Exception as e:
            print(f"🚨 [Executor] 매수 주문 처리 중 예외 발생: {e}")

def execute_sell_orders(sell_orders_df: pd.DataFrame) -> None:
    """매도 주문 목록을 받아 실행하고, 체결된 주문을 DB에 저장합니다."""
    print(f"[Executor] 매도 주문 실행 시작: {len(sell_orders_df)}건")
    if sell_orders_df.empty:
        return

    for _, order in sell_orders_df.iterrows():
        market = order["market"]
        price = order["target_sell_price"]
        volume = order["quantity"]

        try:
            # 최소 주문 금액 체크
            if price * volume < 5000:
                print(f"⚠️ [Executor] {market} 매도 금액 최소 주문 금액 미달 → 스킵")
                continue

            adjusted_price = adjust_price_to_tick(price, ticker=market)
            print(f"🌟 [Executor] 신규 매도 주문: {market}, price={adjusted_price}, volume={volume}")
            response = send_order(market=market, side="ask", ord_type="limit", unit_price=adjusted_price, volume=volume)

            if 'error' in response:
                print(f"❌ [Executor] 주문 실패: {response['error']['message']}")
                continue

            uuid = response.get("uuid")
            if not uuid:
                print(f"❌ [Executor] 주문 후 UUID를 받지 못했습니다: {response}")
                continue

            # 체결 상태 확인 및 DB 저장
            final_order_status = get_order_results_by_uuids_safe([uuid])
            if final_order_status and final_order_status[0].get("state") == "done":
                print(f"✅ [Executor] {market} 매도 주문 체결 완료")
                db_data = final_order_status[0]
                insert_order(db_data, 'sell_orders')

        except Exception as e:
            print(f"🚨 [Executor] 매도 주문 처리 중 예외 발생: {e}")