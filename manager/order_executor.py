import pandas as pd
from api.order import send_order, get_order_results_by_uuids_safe
from utils.price_utils import adjust_price_to_tick
from db.db_utils import insert_order

def execute_buy_orders(buy_orders_df: pd.DataFrame) -> None:
    """
    # --- [주문 실행 ①: 매수] ---
    # 전략(strategy) 계층에서 생성된 매수 계획(DataFrame)을 실제로 실행하는 역할입니다.
    # "너굴의 행동대장"이 "씨앗을 심어라"라는 명령을 수행하는 것과 같습니다.
    """
    print(f"[Executor] 매수 주문 실행 시작: {len(buy_orders_df)}건")
    if buy_orders_df.empty:
        return

    # 실행해야 할 주문 목록을 하나씩 처리합니다.
    for _, order in buy_orders_df.iterrows():
        market = order["market"]
        price = order["target_price"]
        amount = order["buy_amount"]
        buy_type = order["buy_type"]

        try:
            # [안전장치] Upbit의 최소 주문 금액(5000원)보다 낮은 주문은 실행하지 않고 건너뜁니다.
            if (buy_type == 'initial' and amount < 5000) or (buy_type != 'initial' and price * (amount / price) < 5000):
                print(f"⚠️ [Executor] {market} 매수 금액 최소 주문 금액 미달 → 스킵")
                continue

            print(f"🌟 [Executor] 신규 매수 주문: {market}, amount={amount}, price={price}")
            
            # [주문 유형 분기] 주문 유형에 따라 다른 API 파라미터를 사용합니다.
            # initial 주문은 시장가로 즉시 체결, flow 주문은 지정가로 예약합니다.
            if buy_type == "initial":
                response = send_order(market=market, side="bid", ord_type="price", amount_krw=amount)
            else:
                volume = round(amount / price, 8)
                response = send_order(market=market, side="bid", ord_type="limit", unit_price=price, volume=volume)

            # [결과 처리] 주문 후 받은 응답을 확인합니다.
            if 'error' in response:
                print(f"❌ [Executor] 주문 실패: {response['error']['message']}")
                continue

            uuid = response.get("uuid")
            if not uuid:
                print(f"❌ [Executor] 주문 후 UUID를 받지 못했습니다: {response}")
                continue

            # [기록] 주문이 성공적으로 체결되었다면, 그 결과를 데이터베이스에 영구적으로 기록합니다.
            # "부엉의 박물관"에 화석을 기증하는 과정입니다.
            final_order_status = get_order_results_by_uuids_safe([uuid])
            # print(final_order_status)
            # if final_order_status and final_order_status[0].get("state") == "done":
            #     db_data = final_order_status[0]
            if final_order_status:
                print(f"✅ [Executor] {market} 매수 주문 체결 완료")
                for db_data in final_order_status:
                    db_data['created_at'] = db_data['created_at'].replace('+09:00', '')
                    insert_order(db_data, 'buy_orders')

        except Exception as e:
            print(f"🚨 [Executor] 매수 주문 처리 중 예외 발생: {e}")

def execute_sell_orders(sell_orders_df: pd.DataFrame) -> None:
    """
    # --- [주문 실행 ②: 매도] ---
    # 전략(strategy) 계층에서 생성된 매도 계획(DataFrame)을 실제로 실행하는 역할입니다.
    # "너굴의 행동대장"이 "열매를 수확해라"라는 명령을 수행하는 것과 같습니다.
    """
    print(f"[Executor] 매도 주문 실행 시작: {len(sell_orders_df)}건")
    if sell_orders_df.empty:
        return

    for _, order in sell_orders_df.iterrows():
        market = order["market"]
        price = order["target_sell_price"]
        volume = order["quantity"]

        try:
            # [안전장치] 최소 주문 금액 체크
            if price * volume < 5000:
                print(f"⚠️ [Executor] {market} 매도 금액 최소 주문 금액 미달 → 스킵")
                continue

            # [가격 조정] Upbit의 가격 단위(호가 틱)에 맞게 주문 가격을 미세 조정합니다.
            # 이 과정을 거치지 않으면 주문이 거부될 수 있습니다.
            adjusted_price = adjust_price_to_tick(price, ticker=market)
            print(f"🌟 [Executor] 신규 매도 주문: {market}, price={adjusted_price}, volume={volume}")
            
            # [API 호출] 모든 매도 주문은 지정가(limit)로 실행됩니다.
            response = send_order(market=market, side="ask", ord_type="limit", unit_price=adjusted_price, volume=volume)

            if 'error' in response:
                print(f"❌ [Executor] 주문 실패: {response['error']['message']}")
                continue

            uuid = response.get("uuid")
            if not uuid:
                print(f"❌ [Executor] 주문 후 UUID를 받지 못했습니다: {response}")
                continue

            # [기록] 주문이 성공적으로 체결되었다면, 그 결과를 데이터베이스에 기록합니다.
            final_order_status = get_order_results_by_uuids_safe([uuid])
            if final_order_status:
                print(f"ℹ️ [Executor] {market} 매도 주문 상태: {final_order_status[0].get('state')}")
                print(f"✅ [Executor] {market} 매도 주문 정보 DB에 저장")
                for db_data in final_order_status:
                    db_data['created_at'] = db_data['created_at'].replace('+09:00', '')
                    insert_order(db_data, 'sell_orders')

        except Exception as e:
            print(f"🚨 [Executor] 매도 주문 처리 중 예외 발생: {e}")